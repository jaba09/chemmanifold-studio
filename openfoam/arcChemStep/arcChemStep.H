/*---------------------------------------------------------------------------*\
Class
    Foam::arcChemStep

Description
    Direct integration of the analytically reduced mechanism ARC_GRI30_NOx22
    (22 transported species + 21 quasi-steady radicals from a linearized QSSA
    solve, reduced from GRI-Mech 3.0; mechanisms/arc_gri30_nox22).

    OpenFOAM's reaction readers cannot express quasi-steady species, so the
    case lists only the 22 transported species (with an empty reaction list)
    and this chemistry solver integrates each cell's constant-pressure,
    adiabatic ODE y = (Y_1..Y_22, T) over the flow time step with an OpenFOAM
    ODE solver (finite-difference Jacobian). The rates come from the plain-C
    core arc_gri30_nox22.c. After the step the C/H/O/N totals of the cell are
    restored by the report's projection onto CO2/H2O/O2/N2 (the QSSA does not
    conserve elements exactly), and the result goes back as concentrations at
    the cell's starting density, as for every OpenFOAM chemistry solver.

Usage
    system/controlDict:            libs (arcChemStep);
    constant/chemistryProperties:
        chemistryType { solver arcChemStep; method standard; }
        arcChemStepCoeffs
        {
            solver      seulex;   // any OpenFOAM ODE solver
            absTol      1e-12;
            relTol      1e-4;
            T_freeze    0;        // K; colder cells are not advanced
            project     true;     // element projection after each step
            reportCalls 0;        // print counters every this many cells (0 = off)
        }
    constant/reactions:  species (<the 22 names>); reactions {};

SourceFiles
    arcChemStep.C

\*---------------------------------------------------------------------------*/

#ifndef arcChemStep_H
#define arcChemStep_H

#include "chemistrySolver.H"
#include "ODESystem.H"
#include "ODESolver.H"
#include "autoPtr.H"
#include "arc_gri30_nox22.h"

namespace Foam
{

//- The ARC ODE for one cell at fixed pressure
class arcODE
:
    public ODESystem
{
public:

    mutable scalar p_;

    arcODE() : p_(1e5) {}

    virtual label nEqns() const { return ARC_N_ODE + 1; }

    virtual void derivatives
    (
        const scalar x,
        const scalarField& y,
        const label li,
        scalarField& dydx
    ) const;

    virtual void jacobian
    (
        const scalar x,
        const scalarField& y,
        const label li,
        scalarField& dfdx,
        scalarSquareMatrix& dfdy
    ) const;
};


template<class ChemistryModel>
class arcChemStep
:
    public chemistrySolver<ChemistryModel>
{
    // Private data

        dictionary coeffsDict_;
        arcODE ode_;
        mutable autoPtr<ODESolver> odeSolver_;
        mutable scalarField y_;
        //- OpenFOAM species index of each ARC species (first 22)
        labelList toFoam_;
        scalar Tfreeze_;
        bool project_;
        label reportCalls_;
        mutable label nCalls_, nAdvanced_;
        mutable scalar maxElemFix_;

public:

    TypeName("arcChemStep");

    arcChemStep(typename ChemistryModel::reactionThermo& thermo);

    virtual ~arcChemStep() = default;

    virtual void solve
    (
        scalarField& c,
        scalar& T,
        scalar& p,
        scalar& deltaT,
        scalar& subDeltaT
    ) const;
};

} // End namespace Foam

#ifdef NoRepository
    #include "arcChemStep.C"
#endif

#endif
