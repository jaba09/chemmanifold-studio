/*---------------------------------------------------------------------------*\
    Register arcChemStep for the thermo of the quemadorUnico case
    (sutherland / janaf / perfectGas / sensibleEnthalpy = gasHThermoPhysics).
\*---------------------------------------------------------------------------*/

#include "makeChemistrySolverTypes.H"
#include "thermoPhysicsTypes.H"
#include "psiReactionThermo.H"
#include "rhoReactionThermo.H"
#include "arcChemStep.H"

namespace Foam
{
    makeChemistrySolverType(arcChemStep, psiReactionThermo, gasHThermoPhysics);
    makeChemistrySolverType(arcChemStep, rhoReactionThermo, gasHThermoPhysics);
}
