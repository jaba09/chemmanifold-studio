/*---------------------------------------------------------------------------*\
    Register userChemStep for the thermo used by the quemadorUnico case
    (sutherland / janaf / perfectGas / sensibleEnthalpy = gasHThermoPhysics).
    Add more makeChemistrySolverType lines for other thermo types.
\*---------------------------------------------------------------------------*/

#include "makeChemistrySolverTypes.H"
#include "thermoPhysicsTypes.H"
#include "psiReactionThermo.H"
#include "rhoReactionThermo.H"
#include "userChemStep.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
    makeChemistrySolverType(userChemStep, psiReactionThermo, gasHThermoPhysics);
    makeChemistrySolverType(userChemStep, rhoReactionThermo, gasHThermoPhysics);
}

// ************************************************************************* //
