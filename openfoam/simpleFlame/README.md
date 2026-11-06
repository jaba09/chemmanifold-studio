# Simple flame: Fluent vs OpenFOAM

A laminar CH4/air coflow jet flame used to find why the Fluent and OpenFOAM GA18 burner flames
differ. Same nozzle radius (2.5 mm) and CH4 mass flow (6.735e-6 kg/s) as the burner, no burner
geometry, no turbulence, no radiation.

| | |
|---|---|
| Domain | 2D axisymmetric, x 0-0.25 m (axis, up), r 0-0.03 m; 292 x 76 = 22192 quads |
| inlet-fuel | r < 2.5 mm, 0.5263 m/s CH4, 300 K |
| inlet-air | r 2.5-30 mm, 0.2 m/s, Y_O2 0.233 / N2, 300 K |
| outlet | x = 0.12 m, 0 Pa gauge, backflow air 300 K |
| side | r = 0.03 m, symmetry |
| Models | steady (LTS in OpenFOAM), laminar, g = -9.81 x, GA18 laminar finite rate, no radiation |
| Start | cold air 300 K, 0.2 m/s; 2000 K hot box x < 15 mm, r < 8 mm (setFields) |

- `make_mesh.py <case dir>` writes `coflow.msh` (ASCII Fluent mesh) and the identical 5 deg wedge
  polyMesh (same cell order) via `../tools/fluent_h5_to_foam.write_wedge`.
- `solver/rhoReactingBuoyantLeFoam`: v1912 `rhoReactingBuoyantFoam` source (builds against v2412) with
  `constant/speciesDiffusion`:
  - `stock`: rho D_k = mu + mu_t (what the stock solver does: Sc = 1)
  - `unityLewis`: rho D_k = kappa/cp + mu_t/Sct (Fluent "unity-lewis-number")
  - `constantLewis`: rho D_k = kappa/(cp Le_k) + mu_t/Sct, Le_k from a Cantera GA18 counterflow flame
    (mixture-averaged), the closest constant-Le match to Fluent's kinetic-theory diffusion.
  The two non-stock models add div(sum_k hs_k (rho D_k - alphaEff) grad Y_k) to the energy equation.
- `case/Allrun <stock|unityLewis|constantLewis> [run dir]` builds and runs one variant.

Fluent runs (F2 = burner transport, F1 = unity Lewis) are done by replacing the mesh of the burner case;
step-by-step guide: https://claude.ai/artifact/NWtnasY4PLaLzJwmxs5jMp
