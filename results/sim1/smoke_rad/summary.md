# Surrogate smoke test on the radiation case (phase B de-risk)

11 Nov 2026, 14:03-14:21 CET, sim1, 4 ranks. ood8_s0 in pure mode (`userChemStep`, oodFallback false) from the A1r
(R2 with fvDOM radiation) state at t = 0.1 s, 500 steps to 0.11 s. Same case as phase B: corrected outlets, LeFoam +
constantLewis, fvDOM (solverFreq 10), hood non-radiative.

- No crash. Selftest 60/60 (max abs dT 2e-12 K vs PyTorch).
- Cost: **2.20 s/step** on 4 ranks (steps 51-500), with radiation.
- Tmax 2128 K at 0.11 s (A1r DI: 2121 K at 0.1475 s).
- OOD share: **24.6 % of advanced cells** over the 500 steps, rising during the run. The flags come from the manifold
  (z-space) and data-density checks, not from T, p or species range. Old flame without radiation, first 50 steps: under 1 %.
- Shadow DI (one step of the surrogate vs GA18 from the same state, stratified per (T, Z, inside/OOD) bin, 5,531 checks):

| Cells | checks | median abs dT [K] | p95 [K] | max [K] | median DI increment [K] |
|---|---|---|---|---|---|
| inside | 3953 | 0.070 | 2.19 | 20.1 | 0.11 |
| OOD | 1578 | 0.143 | 3.44 | 20.2 | 0.21 |

- Share of shadow-sampled states flagged OOD by time: 8 % at 101 ms, 31 % at 104 ms, 38 % at 110 ms.
- Flagged states: T 600-1829 K (median 1006 K), Z 0.006-0.51 (median 0.035): lean gas cooled by the radiating walls.
  This is the high-heat-loss region that ood8's exploration did not cover (Fluent's hot gas has psi p50 0.42).

Conclusion: phase B can run as planned. Expect the OOD share and the radiation-cooled-gas errors to separate the
candidates. tix2/tix2h explored psi up to 0.80-0.85.
