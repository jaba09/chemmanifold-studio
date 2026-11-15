/*---------------------------------------------------------------------------*\
Class
    Foam::arcDI

Description
    Direct integration (DI) of one cell with the ARC_GRI30_NOx22 kernel, for
    userChemStep built as libuserChemStepArc (-DUSERCHEMSTEP_ARC,
    openfoam/userChemStepArc). It replaces ode<ChemistryModel>::solve, which
    integrates the case's reaction list (GA18): an ARC case lists the 22
    transported species with no reactions, so the ISANN DI phase, OOD cells,
    untrusted bins and shadow checks must call the ARC kernel instead.

    Same algorithm as arcChemStep (openfoam/arcChemStep/arcChemStep.C): the
    constant-pressure adiabatic ODE y = (Y_1..Y_22, T) with an OpenFOAM ODE
    solver and a finite-difference Jacobian, then the C/H/O/N restoration onto
    CO2/H2O/O2/N2 (arc_project), concentrations back at the starting density.

    Settings: userChemStepCoeffs/arc { kernel original; solver seulex;
    absTol 1e-12; relTol 1e-4; project true; } (all optional).

\*---------------------------------------------------------------------------*/

#ifndef arcDI_H
#define arcDI_H

#include "ODESystem.H"
#include "ODESolver.H"
#include "autoPtr.H"
#include "dictionary.H"
#include "arc_gri30_nox22.h"

namespace Foam
{

class arcDIODE
:
    public ODESystem
{
public:

    mutable scalar p_;
    void (*rhs_)(double, const double*, double*);

    arcDIODE() : p_(1e5), rhs_(arc_rhs_original) {}

    virtual label nEqns() const { return ARC_N_ODE + 1; }

    virtual void derivatives(const scalar, const scalarField& y, scalarField& dydx) const
    {
        double yy[ARC_N_ODE + 1], dd[ARC_N_ODE + 1];
        for (int k = 0; k <= ARC_N_ODE; k++) yy[k] = y[k];
        if (yy[ARC_N_ODE] < 200) yy[ARC_N_ODE] = 200;
        rhs_(p_, yy, dd);
        for (int k = 0; k <= ARC_N_ODE; k++) dydx[k] = dd[k];
    }

    virtual void jacobian
    (
        const scalar, const scalarField& y, scalarField& dfdx, scalarSquareMatrix& dfdy
    ) const
    {
        const label n = ARC_N_ODE + 1;
        double yy[ARC_N_ODE + 1], f0[ARC_N_ODE + 1], f1[ARC_N_ODE + 1];
        for (int k = 0; k < n; k++) yy[k] = y[k];
        if (yy[ARC_N_ODE] < 200) yy[ARC_N_ODE] = 200;
        rhs_(p_, yy, f0);
        for (label j = 0; j < n; j++)
        {
            const double y0 = yy[j];
            const double h = (j == ARC_N_ODE) ? 1e-6*max(y0, 300.0) : 1e-7*max(fabs(y0), 1e-9);
            yy[j] = y0 + h;
            rhs_(p_, yy, f1);
            yy[j] = y0;
            for (label i = 0; i < n; i++) dfdy(i, j) = (f1[i] - f0[i])/h;
        }
        for (label i = 0; i < n; i++) dfdx[i] = 0;
    }
};


class arcDI
{
    arcDIODE ode_;
    autoPtr<ODESolver> odeSolver_;
    mutable scalarField y_;
    //- case species index of each ARC species
    labelList toFoam_;
    bool project_;

public:

    //- names / W: the case's species and molecular weights, in case order
    arcDI(const dictionary& dict, const wordList& names, const scalarList& W)
    :
        ode_(),
        y_(ARC_N_ODE + 1, 0.0),
        toFoam_(ARC_N_ODE, -1),
        project_(dict.getOrDefault<bool>("project", true))
    {
        const word kernel(dict.getOrDefault<word>("kernel", "original"));
        if (kernel == "rebuilt") ode_.rhs_ = arc_rhs;
        else if (kernel != "original")
        {
            FatalErrorInFunction << "arc kernel " << kernel << ": original or rebuilt" << exit(FatalError);
        }
        dictionary odeDict(dict);
        if (!odeDict.found("solver")) odeDict.add("solver", "seulex");
        if (!odeDict.found("absTol")) odeDict.add("absTol", 1e-12);
        if (!odeDict.found("relTol")) odeDict.add("relTol", 1e-4);
        odeSolver_ = ODESolver::New(ode_, odeDict);
        if (names.size() != ARC_N_ODE)
        {
            FatalErrorInFunction
                << "libuserChemStepArc needs exactly the " << ARC_N_ODE
                << " ARC_GRI30_NOx22 species, the case has " << names.size() << exit(FatalError);
        }
        for (int k = 0; k < ARC_N_ODE; k++)
        {
            const word n(arc_species_name(k));
            toFoam_[k] = names.find(n);
            if (toFoam_[k] < 0)
            {
                FatalErrorInFunction << "species " << n << " missing from the case" << exit(FatalError);
            }
            if (mag(W[toFoam_[k]] - arc_species_W(k)) > 1e-3)
            {
                FatalErrorInFunction
                    << "molecular weight of " << n << " differs: " << W[toFoam_[k]]
                    << " vs " << arc_species_W(k) << exit(FatalError);
            }
        }
        Info<< "userChemStep: DI with ARC_GRI30_NOx22 (" << ARC_N_ODE << " ODE + " << ARC_N_QSS
            << " QSS species), kernel " << kernel << ", ODE solver " << odeDict.get<word>("solver")
            << ", element projection " << project_ << endl;
    }

    //- One cell over deltaT, as ode<ChemistryModel>::solve (c in kmol/m3, case order)
    void solve(scalarField& c, scalar& T, const scalar p, const scalar deltaT, scalar& subDeltaT) const
    {
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
        for (int k = 0; k < ARC_N_ODE; k++) Y[k] = max(y_[k], 0.0);
        if (project_)
        {
            arc_project(Y, el0);
            for (int k = 0; k < ARC_N_ODE; k++) Y[k] = max(Y[k], 0.0);
        }
        T = y_[ARC_N_ODE];
        for (int k = 0; k < ARC_N_ODE; k++) c[toFoam_[k]] = rho*Y[k]/arc_species_W(k);
    }
};

} // End namespace Foam

#endif
