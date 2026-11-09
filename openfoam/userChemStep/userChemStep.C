/*---------------------------------------------------------------------------*\
    OpenFOAM counterpart of Fluent's DEFINE_CHEM_STEP; see userChemStep.H
\*---------------------------------------------------------------------------*/

#include "userChemStep.H"
#include <cctype>
#include <fstream>
#include <sstream>

namespace
{
    // Bins of the shadow DI check: 100 K bands from 600 K, Z bands around
    // Z_st (0.055), inside / outside the training data
    const double shadowZ[] =
        {0, 0.01, 0.02, 0.03, 0.045, 0.055, 0.07, 0.1, 0.15, 0.22, 0.4, 1.01};
    const int nShadowZ = 11;
    const int nShadowT = 18;
}

// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

template<class ChemistryModel>
Foam::userChemStep<ChemistryModel>::userChemStep
(
    typename ChemistryModel::reactionThermo& thermo
)
:
    ode<ChemistryModel>(thermo),
    coeffsDict_(this->subOrEmptyDict("userChemStepCoeffs")),
    Y_(this->nSpecie()),
    model_(nullptr),
    map_(this->nSpecie(), -1),
    oodFallback_(coeffsDict_.getOrDefault<bool>("oodFallback", false)),
    odeAbove_(coeffsDict_.getOrDefault<scalar>("odeAbove", GREAT)),
    odeInduction_(coeffsDict_.getOrDefault<scalarList>("odeInduction", scalarList())),
    iFuel_(-1), iO2_(-1), nInduction_(0),
    reportCalls_(coeffsDict_.getOrDefault<label>("reportCalls", 0)),
    nCalls_(0), nAdvanced_(0), nFrozen_(0), nOOD_(0), nInvalid_(0), nCapped_(0),
    nFallback_(0),
    dtMin_(GREAT), dtMax_(0),
    shadowEvery_(coeffsDict_.getOrDefault<label>("shadowEvery", 0)),
    shadowPerBin_(coeffsDict_.getOrDefault<label>("shadowPerBin", 2)),
    shadowIndex_(-1),
    shadowCount_(),
    dtHist_(2*80, 0),
    isann_(coeffsDict_.found("isann")),
    isannDict_(coeffsDict_.subOrEmptyDict("isann")),
    isannControl_(isannDict_.getOrDefault<fileName>("control", "isann/control")),
    isannWriteEvery_(isannDict_.getOrDefault<label>("writeEvery", 25)),
    isannActive_(isannDict_.getOrDefault<bool>("startActive", false)), isannVersion_(0), isannStep_(-1),
    iHot_(0), iDI_(0), iOOD_(0), iUntrusted_(0), iANN_(0), iShadow_(0), iShadowBad_(0),
    trustTAbs_(isannDict_.getOrDefault<scalar>("trustTAbs", 1.0)),
    trustRel_(isannDict_.getOrDefault<scalar>("trustRel", 0.3)),
    trustOHAbs_(isannDict_.getOrDefault<scalar>("trustOHAbs", 5e-5)),
    trustMin_(isannDict_.getOrDefault<label>("trustMin", 2)),
    iOHmodel_(-1)
{
    for (label b=0; b<6; b++) nFlag_[b] = 0;
    forAll(this->specieThermo(), i)
    {
        if (this->specieThermo()[i].name() == "CH4") iFuel_ = i;
        if (this->specieThermo()[i].name() == "O2") iO2_ = i;
    }
    if (odeInduction_.size() && (odeInduction_.size() != 4 || iFuel_ < 0 || iO2_ < 0))
    {
        FatalErrorInFunction
            << "odeInduction needs (T_lo T_hi Y_CH4 Y_O2) and species CH4, O2" << exit(FatalError);
    }
    cm_default_options(&options_);
    fileName modelFile;
    if (!coeffsDict_.readIfPresent("model", modelFile))
    {
        Info<< "userChemStep: no model file, using the Fluent manual example" << endl;
        return;
    }
    modelFile.expand();
    options_.T_freeze = coeffsDict_.getOrDefault<scalar>("T_freeze", 600);
    options_.max_substeps = coeffsDict_.getOrDefault<label>("maxSubsteps", 50);
    options_.ood_action = coeffsDict_.getOrDefault<label>("oodAction", 0);
    options_.check_ood = coeffsDict_.getOrDefault<bool>("checkOOD", true);

    char err[512];
    model_ = cm_load(modelFile.c_str(), err, sizeof(err));
    if (!model_)
    {
        FatalErrorInFunction
            << "cannot load " << modelFile << ": " << err << exit(FatalError);
    }

    // Species by name, ignoring case
    const auto& thermos = this->specieThermo();
    const label nModel = cm_n_species(model_);
    forAll(map_, i)
    {
        const word& name = thermos[i].name();
        for (label k=0; k<nModel; k++)
        {
            const char* mk = cm_species_name(model_, k);
            if (label(name.size()) != label(strlen(mk))) continue;
            bool same = true;
            forAll(name, j)
            {
                if (tolower(name[j]) != tolower(mk[j])) { same = false; break; }
            }
            if (same) { map_[i] = k; break; }
        }
        if (map_[i] < 0)
        {
            FatalErrorInFunction
                << "species " << name << " is not in the model " << modelFile
                << exit(FatalError);
        }
    }
    if (nModel != map_.size())
    {
        FatalErrorInFunction
            << "the model has " << nModel << " species, the case "
            << map_.size() << exit(FatalError);
    }

    Info<< "userChemStep: ChemManifold surrogate " << cm_arch(model_)
        << " from " << modelFile << ", trained dt " << cm_dt_min(model_)
        << "-" << cm_dt_max(model_) << " s, T_freeze " << options_.T_freeze
        << " K, maxSubsteps " << options_.max_substeps
        << (oodFallback_ ? ", OOD cells integrated with the ODE solver" : "")
        << endl;
    if (oodFallback_ && !options_.check_ood)
    {
        FatalErrorInFunction
            << "oodFallback needs checkOOD true" << exit(FatalError);
    }

    if (isann_)
    {
        if (!cm_has_ood(model_))
        {
            FatalErrorInFunction
                << "isann needs a model file with OOD tables (the parent)" << exit(FatalError);
        }
        if (oodFallback_)
        {
            FatalErrorInFunction
                << "isann replaces oodFallback: set oodFallback false" << exit(FatalError);
        }
        options_.check_ood = 1;
        store_.reset(new isannStore(Pstream::myProcNo(), this->mesh().time().timeIndex()));
        isannStore& st = *store_;
        st.cap = isannDict_.getOrDefault<label>("capPerBox", 2);
        st.wT = isannDict_.getOrDefault<scalar>("boxT", 25);
        st.wZ = isannDict_.getOrDefault<scalar>("boxSqrtZ", 0.02);
        st.wLogY = isannDict_.getOrDefault<scalar>("boxLogY", 0.25);
        st.wLogDt = isannDict_.getOrDefault<scalar>("boxLogDt", 0.1);
        st.yFloor = isannDict_.getOrDefault<scalar>("boxYFloor", 1e-8);
        const wordList keys(isannDict_.getOrDefault<wordList>
        (
            "boxSpecies", wordList({"CO2", "CO", "OH", "H", "CH4", "O2", "CH2O", "HO2"})
        ));
        for (const word& w : keys)
        {
            forAll(thermos, i)
            {
                if (thermos[i].name() == w) st.keySpecies.push_back(map_[i]);
            }
        }
        forAll(thermos, i)
        {
            if (thermos[i].name() == "OH") iOHmodel_ = map_[i];
        }
        trustN_.setSize(nShadowT*nShadowZ, 0);
        trustBad_.setSize(nShadowT*nShadowZ, 0);
        if (shadowEvery_ <= 0) shadowEvery_ = 10;
        Info<< "userChemStep: ISANN, "
            << (isannActive_ ? "the parent network in use from the start (no DI phase)"
                             : "DI phase (every cell on the ODE solver)")
            << " until " << isannControl_ << " names a model; dedup grid of " << st.keySpecies.size() + 3
            << " coordinates, " << st.cap << " pairs per box" << endl;
    }

    if (shadowEvery_ > 0)
    {
        Info<< "userChemStep: shadow DI check every " << shadowEvery_
            << " time steps, up to " << shadowPerBin_
            << " cells per (T, Z, inside/OOD) bin, written to shadowDI.csv"
            << endl;
    }

    fileName testsFile;
    if (coeffsDict_.readIfPresent("tests", testsFile))
    {
        testsFile.expand();
        char rep[1024];
        const int nFail = cm_selftest(model_, testsFile.c_str(), rep, sizeof(rep));
        Info<< "userChemStep: " << rep << endl;
        if (nFail != 0)
        {
            FatalErrorInFunction
                << "self-test failed (" << nFail << ")" << exit(FatalError);
        }
    }
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

template<class ChemistryModel>
Foam::userChemStep<ChemistryModel>::~userChemStep()
{
    writeDtHistogram();
    if (store_)
    {
        isannBeginStep();     // last status line
        std::vector<std::string> names;
        for (label k=0; k<cm_n_species(model_); k++) names.push_back(cm_species_name(model_, k));
        store_->write(this->mesh().time().path()/"isannPairs.csv", names);
    }
    if (model_)
    {
        cm_free(model_);
    }
}


// * * * * * * * * * * * * * Private Member Functions  * * * * * * * * * * * //

template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::chemStep
(
    scalarField& yk,
    const scalar T,
    const scalar p,
    const scalar dt
) const
{
    if (model_)
    {
        double Y[CM_MAX_SPECIES];
        forAll(yk, i)
        {
            Y[map_[i]] = yk[i];
        }
        cm_info info;
        const int status = cm_advance(model_, &options_, Y, T, p, dt, &info);
        forAll(yk, i)
        {
            yk[i] = Y[map_[i]];
        }

        nCalls_++;
        if (status != 0 || (info.flags & CM_INVALID)) nInvalid_++;
        else if (info.flags & CM_FROZEN) nFrozen_++;
        else nAdvanced_++;
        if (info.flags & CM_OOD_ANY) nOOD_++;
        for (label b=0; b<6; b++)
        {
            if (info.flags & (1u << b)) nFlag_[b]++;
        }
        if (info.flags & CM_DT_CAPPED) nCapped_++;
        dtMin_ = min(dtMin_, dt);
        dtMax_ = max(dtMax_, dt);
        if (reportCalls_ > 0 && nCalls_ >= reportCalls_)
        {
            report();
        }
        return;
    }

    // Fluent manual example of DEFINE_CHEM_STEP (user_chem_step):
    //     dY_k/dt = 1/N - Y_k  =>  Y_k(dt) = (Y_k(0) - 1/N) exp(-dt) + 1/N
    const scalar c = 1.0/yk.size();
    const scalar decay = exp(-dt);

    forAll(yk, i)
    {
        yk[i] = (yk[i] - c)*decay + c;
    }
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::writeDtHistogram() const
{
    label total = 0;
    forAll(dtHist_, i) total += dtHist_[i];
    if (total == 0) return;
    OFstream f(this->mesh().time().path()/"dtHistogram.csv");
    f << "log10_dt_lo,log10_dt_hi,cells_below_T_freeze,cells_above_T_freeze" << nl;
    for (label b=0; b<80; b++)
    {
        f << -8 + 0.1*b << ',' << -8 + 0.1*(b + 1) << ',' << dtHist_[b] << ','
          << dtHist_[80 + b] << nl;
    }
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::report() const
{
    writeDtHistogram();
    // Per processor: chemistry runs cell by cell, so no reduction here
    Pout<< "userChemStep: " << nCalls_ << " calls, " << nAdvanced_
        << " advanced, " << nFrozen_ << " frozen, OOD " << nOOD_
        << " (" << (nAdvanced_ ? 100.0*nOOD_/nAdvanced_ : 0.0)
        << " % of advanced), ODE fallback " << nFallback_ << " (induction " << nInduction_ << "), invalid " << nInvalid_ << ", dt capped " << nCapped_
        << ", dt " << dtMin_ << "-" << dtMax_ << " s; OOD by check: T "
        << nFlag_[0] << ", T|Z " << nFlag_[1] << ", p " << nFlag_[2]
        << ", species " << nFlag_[3] << ", manifold " << nFlag_[4]
        << ", data " << nFlag_[5] << endl;
    nCalls_ = nAdvanced_ = nFrozen_ = nOOD_ = nInvalid_ = nCapped_ = 0;
    nFallback_ = 0;
    nInduction_ = 0;
    for (label b=0; b<6; b++) nFlag_[b] = 0;
    dtMin_ = GREAT;
    dtMax_ = 0;
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::shadow
(
    const scalarField& c,
    const scalar T,
    const scalar p,
    const scalar deltaT
) const
{
    const label timeIndex = this->mesh().time().timeIndex();
    if (timeIndex % shadowEvery_ != 0) return;
    if (timeIndex != shadowIndex_)
    {
        shadowIndex_ = timeIndex;
        shadowCount_.setSize(2*nShadowT*nShadowZ);
        shadowCount_ = 0;
    }

    const label nSpecie = this->nSpecie();
    const auto& thermos = this->specieThermo();
    scalar rho = 0;
    for (label i=0; i<nSpecie; i++) rho += c[i]*thermos[i].W();
    if (rho < VSMALL) return;

    double Y0[CM_MAX_SPECIES];
    for (label i=0; i<nSpecie; i++) Y0[map_[i]] = c[i]*thermos[i].W()/rho;
    cm_info oi{};
    cm_ood(model_, &options_, Y0, T, p, &oi);
    const int ood = (oi.flags & CM_OOD_ANY) ? 1 : 0;
    const int bt = std::min(nShadowT - 1, std::max(0, int((T - 600.0)/100.0)));
    int bz = 0;
    while (bz < nShadowZ - 1 && oi.Z >= shadowZ[bz + 1]) bz++;
    label& n = shadowCount_[(ood*nShadowT + bt)*nShadowZ + bz];
    if (n >= shadowPerBin_) return;
    n++;

    // Surrogate step from this state
    double Ys[CM_MAX_SPECIES];
    for (label k=0; k<nSpecie; k++) Ys[k] = Y0[k];
    cm_info si{};
    cm_advance(model_, &options_, Ys, T, p, deltaT, &si);

    // GA18 (odeCoeffs) from the same state
    scalarField cd(c);
    scalar Td = T, pd = p, dtd = deltaT, subd = deltaT;
    ode<ChemistryModel>::solve(cd, Td, pd, dtd, subd);
    scalar rhod = 0;
    for (label i=0; i<nSpecie; i++) rhod += cd[i]*thermos[i].W();

    if (!shadowFile_)
    {
        shadowFile_.reset(new OFstream(this->mesh().time().path()/"shadowDI.csv"));
        OFstream& f = shadowFile_();
        f << "time,T,p,dt,Z,ood_flags,manifold_ratio,data_ratio,T_surrogate,T_DI";
        for (label k=0; k<nSpecie; k++) f << ",Y0_" << cm_species_name(model_, k);
        for (label k=0; k<nSpecie; k++) f << ",Ys_" << cm_species_name(model_, k);
        for (label k=0; k<nSpecie; k++) f << ",Yd_" << cm_species_name(model_, k);
        f << nl;
    }
    double Yd[CM_MAX_SPECIES];
    for (label i=0; i<nSpecie; i++) Yd[map_[i]] = cd[i]*thermos[i].W()/max(rhod, VSMALL);
    if (isann_ && isannActive_)
    {
        // The shadow pair is a GA18 label too; and it rates the network in this bin
        isannKeep(Y0, T, p, deltaT, oi.Z, Yd, Td, 3);
        iShadow_++;
        if (!ood)
        {
            const bool bad = mag(si.T_out - Td) > max(trustTAbs_, trustRel_*mag(Td - T))
                || (iOHmodel_ >= 0 && mag(Ys[iOHmodel_] - Yd[iOHmodel_])
                    > max(trustOHAbs_, trustRel_*mag(Yd[iOHmodel_] - Y0[iOHmodel_])));
            const label b = trustBin(T, oi.Z);
            trustN_[b] = 0.9*trustN_[b] + 1;
            trustBad_[b] = 0.9*trustBad_[b] + (bad ? 1 : 0);
            if (bad) iShadowBad_++;
        }
    }
    OFstream& f = shadowFile_();
    f.precision(9);
    f << this->mesh().time().value() << ',' << T << ',' << p << ',' << deltaT << ','
      << oi.Z << ',' << oi.flags << ',' << oi.manifold_ratio << ',' << oi.data_ratio << ','
      << si.T_out << ',' << Td;
    for (label k=0; k<nSpecie; k++) f << ',' << Y0[k];
    for (label k=0; k<nSpecie; k++) f << ',' << Ys[k];
    for (label k=0; k<nSpecie; k++) f << ',' << Yd[k];
    f << nl;
}


template<class ChemistryModel>
Foam::label Foam::userChemStep<ChemistryModel>::trustBin(const scalar T, const scalar Z)
{
    const int bt = std::min(nShadowT - 1, std::max(0, int((T - 600.0)/100.0)));
    int bz = 0;
    while (bz < nShadowZ - 1 && Z >= shadowZ[bz + 1]) bz++;
    return bt*nShadowZ + bz;
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::massFractions(const scalarField& c, double* Y) const
{
    const auto& thermos = this->specieThermo();
    scalar rho = 0;
    forAll(c, i) rho += c[i]*thermos[i].W();
    forAll(c, i) Y[map_[i]] = c[i]*thermos[i].W()/max(rho, VSMALL);
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::isannKeep
(
    const double* Y0, const scalar T0, const scalar p, const scalar dt,
    const scalar Z, const double* Y1, const scalar T1, const int reason
) const
{
    const label n = cm_n_species(model_);
    const label step = this->mesh().time().timeIndex();
    const scalar time = this->mesh().time().value();
    const int version = isannVersion_;
    store_->offer
    (
        store_->key(T0, Z, Y0, dt),
        [&](isannRecord& r)
        {
            r.step = step; r.time = time; r.reason = reason; r.version = version;
            r.T0 = T0; r.p = p; r.dt = dt; r.Z = Z; r.T1 = T1;
            r.Y0.assign(Y0, Y0 + n);
            r.Y1.assign(Y1, Y1 + n);
        }
    );
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::isannPoll(const label timeIndex) const
{
    std::ifstream in(fileName(this->mesh().time().globalPath()/isannControl_).c_str());
    if (!in) return;
    label version = 0, fromStep = 0;
    std::string modelFile, keyword;
    while (in >> keyword)
    {
        if (keyword == "version") in >> version;
        else if (keyword == "model") in >> modelFile;
        else if (keyword == "fromStep") in >> fromStep;
    }
    if (version <= isannVersion_ || timeIndex < fromStep || modelFile.empty()) return;

    fileName path(modelFile);
    if (!path.isAbsolute()) path = this->mesh().time().globalPath()/path;
    char err[512];
    cm_model* m = cm_load(path.c_str(), err, sizeof(err));
    if (!m || cm_n_species(m) != cm_n_species(model_))
    {
        Pout<< "userChemStep: ISANN cannot load " << path << ": "
            << (m ? "different species" : err) << ", keeping version " << isannVersion_ << endl;
        if (m) cm_free(m);
        return;
    }
    for (label k=0; k<cm_n_species(m); k++)
    {
        if (strcmp(cm_species_name(m, k), cm_species_name(model_, k)) != 0)
        {
            Pout<< "userChemStep: ISANN " << path << " orders the species differently, ignored" << endl;
            cm_free(m);
            return;
        }
    }
    cm_free(model_);
    model_ = m;
    isannVersion_ = version;
    isannActive_ = true;
    trustN_ = 0;
    trustBad_ = 0;
    if (Pstream::master())
    {
        Info<< "userChemStep: ISANN version " << version << " (" << path
            << ") in use from step " << timeIndex << endl;
    }
}


template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::isannBeginStep() const
{
    const label timeIndex = this->mesh().time().timeIndex();
    if (isannStep_ >= 0)
    {
        if (!isannStatus_)
        {
            // appended to, so a restarted run keeps the status of the steps before the restart
            const fileName path(this->mesh().time().path()/"isannStatus.csv");
            const bool exists = isFile(path);
            isannStatus_.reset(new OFstream(path, IOstreamOption(), IOstreamOption::APPEND));
            if (!exists)
            {
                isannStatus_() << "step,version,hot,di_phase,ood,untrusted,ann,shadow,shadow_bad,"
                    "candidates,stored,boxes,replaced,untrusted_bins" << nl;
            }
        }
        label nUntrusted = 0;
        forAll(trustBad_, b)
        {
            if (trustBad_[b] >= trustMin_ && trustBad_[b] > 0.5*trustN_[b]) nUntrusted++;
        }
        isannStatus_() << isannStep_ << ',' << isannVersion_ << ',' << iHot_ << ',' << iDI_ << ','
            << iOOD_ << ',' << iUntrusted_ << ',' << iANN_ << ',' << iShadow_ << ',' << iShadowBad_ << ','
            << store_->nCandidates << ',' << store_->nStored() << ',' << store_->nBoxes() << ','
            << store_->nReplaced << ',' << nUntrusted << endl;
        if (isannWriteEvery_ > 0 && isannStep_ % isannWriteEvery_ == 0)
        {
            std::vector<std::string> names;
            for (label k=0; k<cm_n_species(model_); k++) names.push_back(cm_species_name(model_, k));
            store_->write(this->mesh().time().path()/"isannPairs.csv", names);
        }
    }
    iHot_ = iDI_ = iOOD_ = iUntrusted_ = iANN_ = iShadow_ = iShadowBad_ = 0;
    isannStep_ = timeIndex;
    isannPoll(timeIndex);
}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

template<class ChemistryModel>
void Foam::userChemStep<ChemistryModel>::solve
(
    scalarField& c,
    scalar& T,
    scalar& p,
    scalar& deltaT,
    scalar& subDeltaT
) const
{
    const label nSpecie = this->nSpecie();
    const auto& thermos = this->specieThermo();

    // Concentrations [kmol/m3] -> mass fractions, at the cell density
    scalar rho = 0;
    for (label i=0; i<nSpecie; i++)
    {
        rho += c[i]*thermos[i].W();
    }
    if (rho < VSMALL)
    {
        return;
    }
    for (label i=0; i<nSpecie; i++)
    {
        Y_[i] = c[i]*thermos[i].W()/rho;
    }

    {
        const label b = std::min(79, std::max(0, int(floor((log10(max(deltaT, 1e-30)) + 8.0)/0.1))));
        dtHist_[(T >= options_.T_freeze ? 80 : 0) + b]++;
    }

    if (isann_)
    {
        if (this->mesh().time().timeIndex() != isannStep_) isannBeginStep();
        double Y0[CM_MAX_SPECIES];
        forAll(Y_, i) Y0[map_[i]] = Y_[i];
        cm_info info{};
        int reason = -1;
        if (T >= options_.T_freeze)
        {
            iHot_++;
            cm_ood(model_, &options_, Y0, T, p, &info);
            if (!isannActive_) reason = 0;
            else if (info.flags & CM_OOD_ANY) reason = 1;
            else
            {
                const label b = trustBin(T, info.Z);
                if (trustBad_[b] >= trustMin_ && trustBad_[b] > 0.5*trustN_[b]) reason = 2;
            }
        }
        else if (!isannActive_)
        {
            // DI phase: cold cells on GA18 too, as in the DI run, but not kept
            ode<ChemistryModel>::solve(c, T, p, deltaT, subDeltaT);
            return;
        }
        if (reason < 0 && isannActive_ && shadowEvery_ > 0 && T >= options_.T_freeze)
        {
            shadow(c, T, p, deltaT);
        }
        if (reason >= 0)
        {
            const scalar T0 = T;
            ode<ChemistryModel>::solve(c, T, p, deltaT, subDeltaT);
            double Y1[CM_MAX_SPECIES];
            massFractions(c, Y1);
            isannKeep(Y0, T0, p, deltaT, info.Z, Y1, T, reason);
            if (reason == 0) iDI_++;
            else if (reason == 1) iOOD_++;
            else iUntrusted_++;
            return;
        }
        if (T >= options_.T_freeze) iANN_++;
        chemStep(Y_, T, p, deltaT);
        for (label i=0; i<nSpecie; i++)
        {
            c[i] = max(0.0, rho*Y_[i]/thermos[i].W());
        }
        subDeltaT = deltaT;
        return;
    }

    // Shadow DI check (comparison only; the cell's update below is unchanged)
    if (shadowEvery_ > 0 && model_ && T >= options_.T_freeze)
    {
        shadow(c, T, p, deltaT);
    }

    // Cells outside the training data: integrate them with the ODE solver
    if (oodFallback_ && model_ && T >= options_.T_freeze)
    {
        double Y[CM_MAX_SPECIES];
        forAll(Y_, i)
        {
            Y[map_[i]] = Y_[i];
        }
        cm_info info{};     // cm_ood only sets the OOD bits it finds
        cm_ood(model_, &options_, Y, T, p, &info);
        const bool induction = odeInduction_.size() && T >= odeInduction_[0] && T < odeInduction_[1]
            && Y_[iFuel_] > odeInduction_[2] && Y_[iO2_] > odeInduction_[3];
        if ((info.flags & CM_OOD_ANY) || T >= odeAbove_ || induction)
        {
            nCalls_++;
            nAdvanced_++;
            if (info.flags & CM_OOD_ANY) nOOD_++;
            else if (induction) nInduction_++;
            nFallback_++;
            for (label b=0; b<6; b++)
            {
                if (info.flags & (1u << b)) nFlag_[b]++;
            }
            ode<ChemistryModel>::solve(c, T, p, deltaT, subDeltaT);
            if (reportCalls_ > 0 && nCalls_ >= reportCalls_)
            {
                report();
            }
            return;
        }
    }

    chemStep(Y_, T, p, deltaT);

    for (label i=0; i<nSpecie; i++)
    {
        c[i] = max(0.0, rho*Y_[i]/thermos[i].W());
    }

    // The whole step is taken in one call (no sub-stepping); report deltaT
    // as the chemical time scale so local time stepping is not restricted
    subDeltaT = deltaT;
}


// ************************************************************************* //
