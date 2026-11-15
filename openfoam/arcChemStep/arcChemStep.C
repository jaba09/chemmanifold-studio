/*---------------------------------------------------------------------------*\
    ARC_GRI30_NOx22 chemistry solver; see arcChemStep.H
\*---------------------------------------------------------------------------*/

#include "arcChemStep.H"

// * * * * * * * * * * * * * * * * arcODE  * * * * * * * * * * * * * * * * * //

inline void Foam::arcODE::derivatives
(
    const scalar x,
    const scalarField& y,
    scalarField& dydx
) const
{
    double yy[ARC_N_ODE + 1], dd[ARC_N_ODE + 1];
    for (int k = 0; k <= ARC_N_ODE; k++) yy[k] = y[k];
    if (yy[ARC_N_ODE] < 200) yy[ARC_N_ODE] = 200;
    arc_rhs(p_, yy, dd);
    for (int k = 0; k <= ARC_N_ODE; k++) dydx[k] = dd[k];
}


inline void Foam::arcODE::jacobian
(
    const scalar x,
    const scalarField& y,
    scalarField& dfdx,
    scalarSquareMatrix& dfdy
) const
{
    const label n = ARC_N_ODE + 1;
    double yy[ARC_N_ODE + 1], f0[ARC_N_ODE + 1], f1[ARC_N_ODE + 1];
    for (int k = 0; k < n; k++) yy[k] = y[k];
    if (yy[ARC_N_ODE] < 200) yy[ARC_N_ODE] = 200;
    arc_rhs(p_, yy, f0);
    for (label j = 0; j < n; j++)
    {
        const double y0 = yy[j];
        const double h = (j == ARC_N_ODE)
            ? 1e-6*max(y0, 300.0)
            : 1e-7*max(fabs(y0), 1e-9);
        yy[j] = y0 + h;
        arc_rhs(p_, yy, f1);
        yy[j] = y0;
        for (label i = 0; i < n; i++) dfdy(i, j) = (f1[i] - f0[i])/h;
    }
    for (label i = 0; i < n; i++) dfdx[i] = 0;
}


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

template<class ChemistryModel>
Foam::arcChemStep<ChemistryModel>::arcChemStep
(
    typename ChemistryModel::reactionThermo& thermo
)
:
    chemistrySolver<ChemistryModel>(thermo),
    coeffsDict_(this->subOrEmptyDict("arcChemStepCoeffs")),
    ode_(),
    odeSolver_(),
    y_(ARC_N_ODE + 1, 0.0),
    toFoam_(ARC_N_ODE, -1),
    Tfreeze_(coeffsDict_.getOrDefault<scalar>("T_freeze", 0)),
    project_(coeffsDict_.getOrDefault<bool>("project", true)),
    reportCalls_(coeffsDict_.getOrDefault<label>("reportCalls", 0)),
    nCalls_(0), nAdvanced_(0), maxElemFix_(0)
{
    dictionary odeDict(coeffsDict_);
    if (!odeDict.found("solver")) odeDict.add("solver", "seulex");
    if (!odeDict.found("absTol")) odeDict.add("absTol", 1e-12);
    if (!odeDict.found("relTol")) odeDict.add("relTol", 1e-4);
    odeSolver_ = ODESolver::New(ode_, odeDict);

    const auto& names = this->thermo().composition().species();
    if (names.size() != ARC_N_ODE)
    {
        FatalErrorInFunction
            << "arcChemStep needs exactly the " << ARC_N_ODE
            << " ARC_GRI30_NOx22 transported species, the case has "
            << names.size() << exit(FatalError);
    }
    const auto& thermos = this->specieThermo();
    for (int k = 0; k < ARC_N_ODE; k++)
    {
        const word n(arc_species_name(k));
        if (!names.found(n))
        {
            FatalErrorInFunction
                << "species " << n << " missing from the case" << exit(FatalError);
        }
        toFoam_[k] = names[n];
        const scalar dW = mag(thermos[toFoam_[k]].W() - arc_species_W(k));
        if (dW > 1e-3)
        {
            FatalErrorInFunction
                << "molecular weight of " << n << " differs: "
                << thermos[toFoam_[k]].W() << " vs " << arc_species_W(k)
                << exit(FatalError);
        }
    }
    Info<< "arcChemStep: ARC_GRI30_NOx22, " << ARC_N_ODE << " ODE + "
        << ARC_N_QSS << " QSS species, ODE solver "
        << odeDict.get<word>("solver") << ", T_freeze " << Tfreeze_
        << ", element projection " << project_ << endl;
}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

template<class ChemistryModel>
void Foam::arcChemStep<ChemistryModel>::solve
(
    scalarField& c,
    scalar& T,
    scalar& p,
    scalar& deltaT,
    scalar& subDeltaT
) const
{
    nCalls_++;
    if (T < Tfreeze_) return;

    double Y[ARC_N_ODE];
    scalar rho = 0;
    for (int k = 0; k < ARC_N_ODE; k++) rho += c[toFoam_[k]]*arc_species_W(k);
    if (rho < VSMALL) return;
    for (int k = 0; k < ARC_N_ODE; k++)
    {
        Y[k] = max(c[toFoam_[k]], 0.0)*arc_species_W(k)/rho;
        y_[k] = Y[k];
    }
    y_[ARC_N_ODE] = T;
    double el0[4];
    arc_elements(Y, el0);

    ode_.p_ = p;
    scalar dt = subDeltaT;
    if (!(dt > 0) || dt > deltaT) dt = deltaT;
    odeSolver_->solve(0, deltaT, y_, dt);
    subDeltaT = dt;
    nAdvanced_++;

    for (int k = 0; k < ARC_N_ODE; k++) Y[k] = max(y_[k], 0.0);
    if (project_)
    {
        double el1[4];
        arc_elements(Y, el1);
        for (int e = 0; e < 4; e++)
        {
            if (el0[e] > 0)
                maxElemFix_ = max(maxElemFix_, mag(el1[e] - el0[e])/el0[e]);
        }
        arc_project(Y, el0);
        for (int k = 0; k < ARC_N_ODE; k++) Y[k] = max(Y[k], 0.0);
    }
    T = y_[ARC_N_ODE];
    for (int k = 0; k < ARC_N_ODE; k++) c[toFoam_[k]] = rho*Y[k]/arc_species_W(k);

    if (reportCalls_ > 0 && nCalls_ >= reportCalls_)
    {
        Pout<< "arcChemStep: " << nCalls_ << " cells, " << nAdvanced_
            << " advanced, max element fix " << maxElemFix_ << endl;
        nCalls_ = 0; nAdvanced_ = 0; maxElemFix_ = 0;
    }
}

// ************************************************************************* //
