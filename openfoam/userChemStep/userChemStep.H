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

    The chemStep() shipped here is the Fluent manual example
    (dY_k/dt = 1/N - Y_k, integrated exactly). Replace it with the surrogate
    (e.g. a TorchScript or ONNX model of Y(t+dt) = F(Y, T, p, dt)).

Usage
    system/controlDict:          libs (userChemStep);
    constant/chemistryProperties:
        chemistryType { solver userChemStep; method standard; }
        userChemStepCoeffs { }

SourceFiles
    userChemStep.C

\*---------------------------------------------------------------------------*/

#ifndef userChemStep_H
#define userChemStep_H

#include "chemistrySolver.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

/*---------------------------------------------------------------------------*\
                        Class userChemStep Declaration
\*---------------------------------------------------------------------------*/

template<class ChemistryModel>
class userChemStep
:
    public chemistrySolver<ChemistryModel>
{
    // Private data

        //- Coefficients sub-dictionary (userChemStepCoeffs)
        dictionary coeffsDict_;

        //- Work array of mass fractions
        mutable scalarField Y_;


    // Private Member Functions

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
    virtual ~userChemStep() = default;


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
