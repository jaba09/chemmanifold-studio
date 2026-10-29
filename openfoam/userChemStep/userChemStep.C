/*---------------------------------------------------------------------------*\
    OpenFOAM counterpart of Fluent's DEFINE_CHEM_STEP; see userChemStep.H
\*---------------------------------------------------------------------------*/

#include "userChemStep.H"
#include <cctype>

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
    reportCalls_(coeffsDict_.getOrDefault<label>("reportCalls", 0)),
    nCalls_(0), nAdvanced_(0), nFrozen_(0), nOOD_(0), nInvalid_(0), nCapped_(0),
    nFallback_(0),
    dtMin_(GREAT), dtMax_(0),
    shadowEvery_(coeffsDict_.getOrDefault<label>("shadowEvery", 0)),
    shadowPerBin_(coeffsDict_.getOrDefault<label>("shadowPerBin", 2)),
    shadowIndex_(-1),
    shadowCount_()
{
    for (label b=0; b<6; b++) nFlag_[b] = 0;
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
void Foam::userChemStep<ChemistryModel>::report() const
{
    // Per processor: chemistry runs cell by cell, so no reduction here
    Pout<< "userChemStep: " << nCalls_ << " calls, " << nAdvanced_
        << " advanced, " << nFrozen_ << " frozen, OOD " << nOOD_
        << " (" << (nAdvanced_ ? 100.0*nOOD_/nAdvanced_ : 0.0)
        << " % of advanced), ODE fallback " << nFallback_ << ", invalid " << nInvalid_ << ", dt capped " << nCapped_
        << ", dt " << dtMin_ << "-" << dtMax_ << " s; OOD by check: T "
        << nFlag_[0] << ", T|Z " << nFlag_[1] << ", p " << nFlag_[2]
        << ", species " << nFlag_[3] << ", manifold " << nFlag_[4]
        << ", data " << nFlag_[5] << endl;
    nCalls_ = nAdvanced_ = nFrozen_ = nOOD_ = nInvalid_ = nCapped_ = 0;
    nFallback_ = 0;
    for (label b=0; b<6; b++) nFlag_[b] = 0;
    dtMin_ = GREAT;
    dtMax_ = 0;
}


namespace
{
    // Bins of the shadow DI check: 100 K bands from 600 K, Z bands around
    // Z_st (0.055), inside / outside the training data
    const double shadowZ[] =
        {0, 0.01, 0.02, 0.03, 0.045, 0.055, 0.07, 0.1, 0.15, 0.22, 0.4, 1.01};
    const int nShadowZ = 11;
    const int nShadowT = 18;
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
        if (info.flags & CM_OOD_ANY)
        {
            nCalls_++;
            nAdvanced_++;
            nOOD_++;
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
