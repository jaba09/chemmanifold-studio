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
                                 //  the ODE solver (a test of the coupling: 0 = all cells)
            odeInduction ();     // (T_lo T_hi Y_CH4 Y_O2): with oodFallback, flammable unburnt
                                 //  gas (T in [T_lo, T_hi), CH4 and O2 above) goes to the ODE solver
            isann        { ... } // optional: online learning (ISANN), see below
        }

    ISANN (isann sub-dictionary, replaces oodFallback): the run starts with
    every cell on the ODE solver (GA18) while the (state, dt, GA18 result)
    pairs of the hot cells are kept, deduplicated, in isannPairs.csv of each processor directory
    (isannStore.H). The `model` file is then only the parent whose tables give
    Z and the OOD checks. openfoam/isann/isann.py trains a network on those
    pairs and writes the control file; from the step it names, each rank loads
    that model and uses it on the cells it does not flag as OOD. OOD cells, and
    cells of (T, Z) bins where the shadow check found the network wrong, stay
    on GA18 and their pairs keep being collected for the next training.
        isann
        {
            control      "isann/control"; // case-relative: version N / model <file> / fromStep K
            startActive  false;  // true: no DI phase, the parent network is used from step 1
            writeEvery   25;     // steps between rewrites of isannPairs.csv / isannStatus.csv
            capPerBox    2;      // pairs kept per dedup grid box (reservoir replacement)
            boxT 25; boxSqrtZ 0.02; boxLogY 0.25; boxLogDt 0.1; boxYFloor 1e-8;
            boxSpecies   (CO2 CO OH H CH4 O2 CH2O HO2);
            trustTAbs    1;      // K: shadow check fails if |T_ann - T_DI| > max(trustTAbs,
            trustRel     0.3;    //  trustRel |T_DI - T0|), or the same for OH with trustOHAbs
            trustOHAbs   5e-5;
            trustMin     2;      // failed checks before a bin is untrusted (and > half of them)
        }

SourceFiles
    userChemStep.C

\*---------------------------------------------------------------------------*/

#ifndef userChemStep_H
#define userChemStep_H

#include "ode.H"
#include "OFstream.H"
#include "chemmanifold_core.h"
#include "isannStore.H"
#include <memory>

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
        mutable cm_model* model_;

        //- Surrogate options
        cm_options options_;

        //- OpenFOAM species index -> model species index
        labelList map_;

        //- Integrate cells outside the training data with the ODE solver
        bool oodFallback_;

        //- With oodFallback: cells at or above this T go to the ODE solver too
        scalar odeAbove_;

        //- With oodFallback: (T_lo T_hi Y_CH4 Y_O2) of the induction cells sent to the ODE solver
        scalarList odeInduction_;

        //- OpenFOAM indices of CH4 and O2 (-1 if absent)
        label iFuel_, iO2_;

        //- Cells sent to the ODE solver by odeInduction since the last report
        mutable label nInduction_;

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

        // ISANN (online learning, isann sub-dictionary)

            bool isann_;
            dictionary isannDict_;
            fileName isannControl_;
            label isannWriteEvery_;
            mutable std::unique_ptr<isannStore> store_;
            //- The network is in use (false: DI phase, every cell on GA18)
            mutable bool isannActive_;
            mutable label isannVersion_, isannStep_;
            //- Per-step counters: hot cells, GA18 in the DI phase, GA18 OOD,
            //  GA18 untrusted bin, network, shadow checks, failed checks
            mutable label iHot_, iDI_, iOOD_, iUntrusted_, iANN_, iShadow_, iShadowBad_;
            mutable autoPtr<OFstream> isannStatus_;
            scalar trustTAbs_, trustRel_, trustOHAbs_;
            label trustMin_, iOHmodel_;
            //- Shadow-check statistics per inside (T, Z) bin: checks and failures
            //  (decayed by 0.9 per check), reset when a new model is loaded
            mutable scalarField trustN_, trustBad_;

            //- New flow step: status line, pairs file, control file
            void isannBeginStep() const;

            //- Load the model of the control file if it is due
            void isannPoll(const label timeIndex) const;

            //- Offer a GA18 pair to the store
            void isannKeep
            (
                const double* Y0, const scalar T0, const scalar p, const scalar dt,
                const scalar Z, const double* Y1, const scalar T1, const int reason
            ) const;

            //- Index of the inside (T, Z) bin of the shadow check
            static label trustBin(const scalar T, const scalar Z);

            //- Mass fractions in model order from concentrations
            void massFractions(const scalarField& c, double* Y) const;

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
