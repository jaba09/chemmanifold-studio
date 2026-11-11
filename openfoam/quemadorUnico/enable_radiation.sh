#!/bin/bash
# Add Fluent's wall radiation to a burner case (G1 diagnosis, results/sim1/A1/G1.md).
# Fluent (.cas.h5): DO radiation, gas absorption coefficient 0 (transparent gas), every wall black
# (internal/external emissivity 1, zero thickness), openings black at 300 K. OpenFOAM equivalent:
#   fvDOM (nPhi 4, nTheta 4 -> 64 rays on the wedge), absorptionEmissionModel none, black boundaries,
#   radiation as an fvOption (rhoReactingBuoyantLeFoam passes fvOptions to the energy equation),
#   radiation-aware wall BCs: Fluent's zero-heat-flux walls get zero TOTAL flux (convection + qr),
#   the convective pot walls keep h 15 W/m2K to 323 K plus qr; the hood baffle stays non-radiative (see below).
# Checked on the Fluent field with Fluent's wall temperatures (sim1, 10 Nov 2026): pot bottom emits 27.1 W/rad
# (Fluent 25.1), pot side 3.3 (3.2), disk absorbs 13.1 (12.2).
#   enable_radiation.sh <case> [time dir, default 0] [ILambda source time dir for a warm start]
set -e
C=$(realpath "${1:?case}"); T=${2:-0}; WARM=${3:-}
cd "$C"
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
cat > constant/fvOptions <<'X'
FoamFile { version 2.0; format ascii; class dictionary; object fvOptions; }
radiation { type radiation; libs (radiationModels); }
X
cat > constant/radiationProperties <<'X'
FoamFile { version 2.0; format ascii; class dictionary; object radiationProperties; }
// Fluent: DO, gas absorption 0, black walls; see enable_radiation.sh
radiation       on;
radiationModel  fvDOM;
fvDOMCoeffs { nPhi 4; nTheta 4; tolerance 1e-4; maxIter 3; }
solverFreq      10;             // flow steps per radiation solve (dt 2e-5 s -> every 0.2 ms)
absorptionEmissionModel none;
scatterModel    none;
sootModel       none;
transmissivityModel none;
X
cat > constant/boundaryRadiationProperties <<'X'
FoamFile { version 2.0; format ascii; class dictionary; object boundaryRadiationProperties; }
".*" { type lookup; emissivity 1; absorptivity 1; transmissivity 0; }   // Fluent: in-emiss 1 everywhere
X
cat > "$T/IDefault" <<'X'
FoamFile { version 2.0; format ascii; class volScalarField; object IDefault; }
dimensions [1 0 -3 0 0 0 0];
internalField uniform 0;
boundaryField
{
    ".*"           { type greyDiffusiveRadiation; value uniform 0; }
    "(front|back)" { type wedge; }
}
X
D "divSchemes/div(Ji,Ii_h)" "bounded Gauss linearUpwind grad(Ii_h)" system/fvSchemes
D "solvers/Ii" "{ solver GAMG; tolerance 1e-4; relTol 0; smoother symGaussSeidel; maxIter 5; nPostSweeps 1; }" system/fvSolution
# wall BCs (T must be ASCII)
for p in wall-pot-fff-fluid-fuel outlet-lab-026; do      # Fluent: heat flux 0 (total)
    D "boundaryField/$p" "{ type externalWallHeatFluxTemperature; mode flux; q uniform 0; qr qr; kappaMethod fluidThermo; value uniform 600; }" "$T/T"
done
for p in wall-pot-fff-fluid-mixing wall-pot-fff-fluid-exhaust; do   # Fluent: convection h 15, Tinf 323
    D "boundaryField/$p/qr" qr "$T/T"
done
# hood (Fluent: coupled thin wall): kept as the plain coupled baffle WITHOUT qr. With
# turbulentTemperatureRadCoupledMixed on both sides of the zero-thickness baffle the chimney gas next to it
# cooled without bound (300 -> 52 K in 25 ms, then an FPE; sim1 A1r, 11 Nov). Fluent's net hood radiation
# is only about +-1.8 W/rad, so the hood stays non-radiative.
if [ -n "$WARM" ]; then cp "$WARM"/ILambda_* "$T/"; echo "warm start: $(ls "$WARM"/ILambda_* | wc -l) ray fields from $WARM"; fi
echo "radiation enabled in $C ($T)"
