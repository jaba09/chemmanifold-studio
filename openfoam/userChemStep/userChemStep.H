/*---------------------------------------------------------------------------*\
Class
    Foam::userChemStep

Description
    OpenFOAM counterpart of Fluent's DEFINE_CHEM_STEP hook: a chemistry solver
    that receives each cell's state at the start of a flow time step and
    returns the composition at its end, replacing the ODE integration.

    Fluent passes mass fractions yk, pressure, temperature and dt; OpenFOAM's
    chemistrySolver interface passes molar concentrations c [kmol/m3]. solve()
    converts c -> Y, calls chemStep() and converts back at constant density,
    so chemStep() has exactly the Fluent UDF signature. The reaction rates
    are then RR_i = rho (Y_i(dt) - Y_i(0)) / dt, as in Fluent.

    chemStep() runs one of two bodies:
      - without a model file: the Fluent manual example
        (dY_k/dt = 1/N - Y_k, integrated exactly);
      - with userChemStepCoeffs/model set: the ChemManifold surrogate, through
        the same plain-C core as the Fluent UDF (fluent/udf/chemmanifold_core.c,
        model file written by scripts/12_export_fluent.py). It advances Y at
        constant p and h with sub-steps inside the trained dt range and checks
        whether each state is inside the sampled training space (OOD).

Usage
    system/controlDict:          libs (userChemStep);
    constant/chemistryProperties:
        chemistryType { solver userChemStep; method standard; }
        userChemStepCoeffs
        {
            model        "chemmanifold_model.txt";  // omit for the Fluent example
            tests        "chemmanifold_tests.txt";  // optional: self-test on load
            T_freeze     600;    // K; colder cells are not advanced
            maxSubsteps  50;     // surrogate steps per call at most
            oodAction    0;      // 0 = flag OOD cells only, 1 = leave them unreacted
            checkOOD     true;
            reportCalls  0;      // print counters every this many cell calls (0 = off)
            oodFallback  false;  // true: integrate OOD cells with the ODE solver
                                 //  (odeCoeffs) instead of the surrogate
            odeAbove     1e30;   // K; with oodFallback, cells at or above this T also go to
        }                        //  the ODE solver (a test of the coupling: 0 = all cells)

SourceFiles
    userChemStep.C

\*---------------------------------------------------------------------------*/

#ifndef userChemStep_H
#define userChemStep_H

#include "ode.H"
#include "OFstream.H"
#include "chemmanifold_core.h"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

/*---------------------------------------------------------------------------*\
                        Class userChemStep Declaration
\*---------------------------------------------------------------------------*/

template<class ChemistryModel>
class userChemStep
:
    public ode<ChemistryModel>
{
    // Private data

        //- Coefficients sub-dictionary (userChemStepCoeffs)
        dictionary coeffsDict_;

        //- Work array of mass fractions
        mutable scalarField Y_;

        //- Surrogate model (nullptr: Fluent manual example)
        cm_model* model_;

        //- Surrogate options
        cm_options options_;

        //- OpenFOAM species index -> model species index
        labelList map_;

        //- Integrate cells outside the training data with the ODE solver
        bool oodFallback_;

        //- With oodFallback: cells at or above this T go to the ODE solver too
        scalar odeAbove_;

        //- Print the counters every this many calls (0 = never)
        label reportCalls_;

        //- Counters since the last report: calls, advanced, frozen, OOD, invalid, capped
        mutable label nCalls_, nAdvanced_, nFrozen_, nOOD_, nInvalid_, nCapped_;
        mutable label nFallback_;
        mutable scalar dtMin_, dtMax_;

        //- Cells per OOD check: T, T|Z, p, species, manifold, data
        mutable label nFlag_[6];

        //- Shadow DI check: every shadowEvery_ time steps (0 = off), up to
        //  shadowPerBin_ cells per (T, Z, inside/OOD) bin are also integrated
        //  with GA18 (odeCoeffs) from the same state, and both results are
        //  written to shadowDI.csv; the cell keeps its normal update
        label shadowEvery_;
        label shadowPerBin_;
        mutable label shadowIndex_;
        mutable labelList shadowCount_;
        mutable autoPtr<OFstream> shadowFile_;

        //- Histogram of the chemistry time steps (counts only, no values):
        //  log10(dt) bins of 0.1 from 1e-8 s to 1 s, for cells below and
        //  above T_freeze; rewritten to dtHistogram.csv at each report
        mutable List<label> dtHist_;

        //- Write dtHistogram.csv
        void writeDtHistogram() const;

        //- Run the shadow check on this cell if its bin still has room
        void shadow
        (
            const scalarField& c,
            const scalar T,
            const scalar p,
            const scalar deltaT
        ) const;


    // Private Member Functions

        //- Print and reset the counters
        void report() const;

        //- Advance the mass fractions yk over dt: the DEFINE_CHEM_STEP body
        void chemStep
        (
            scalarField& yk,
            const scalar T,
            const scalar p,
            const scalar dt
        ) const;


public:

    //- Runtime type information
    TypeName("userChemStep");


    // Constructors

        //- Construct from thermo
        userChemStep(typename ChemistryModel::reactionThermo& thermo);


    //- Destructor
    virtual ~userChemStep();


    // Member Functions

        //- Advance the concentrations over deltaT
        virtual void solve
        (
            scalarField& c,
            scalar& T,
            scalar& p,
            scalar& deltaT,
            scalar& subDeltaT
        ) const;
};


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#ifdef NoRepository
    #include "userChemStep.C"
#endif

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
