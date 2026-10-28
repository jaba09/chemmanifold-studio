/*---------------------------------------------------------------------------*\
    OpenFOAM counterpart of Fluent's DEFINE_CHEM_STEP; see userChemStep.H
\*---------------------------------------------------------------------------*/

#include "userChemStep.H"

// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

template<class ChemistryModel>
Foam::userChemStep<ChemistryModel>::userChemStep
(
    typename ChemistryModel::reactionThermo& thermo
)
:
    chemistrySolver<ChemistryModel>(thermo),
    coeffsDict_(this->subOrEmptyDict("userChemStepCoeffs")),
    Y_(this->nSpecie())
{}


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
    // Fluent manual example of DEFINE_CHEM_STEP (user_chem_step):
    //     dY_k/dt = 1/N - Y_k  =>  Y_k(dt) = (Y_k(0) - 1/N) exp(-dt) + 1/N
    const scalar c = 1.0/yk.size();
    const scalar decay = exp(-dt);

    forAll(yk, i)
    {
        yk[i] = (yk[i] - c)*decay + c;
    }
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
