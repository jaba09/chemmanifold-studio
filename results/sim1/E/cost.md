# Phase E: chemistry cost at matched accuracy (sim1, 4 ranks per case)

200 steps of 2e-5 s from the A1r (R2rad) state at t = 0.1 s, same case and radiation as protocol v2. Two cases ran at a time (8 cores) next to C2's 8, so absolute times include the machine's load; ratios are the point. Chemistry s/step = total - flow only. Per cell = CPU-us per chemistry cell per step. Error = the 0.104 s state against the DI case (hot cells T > 600 K in DI, volume-weighted).

| Case | s/step | chemistry s/step | cells with chemistry | CPU-us / cell-step | chemistry speed-up vs DI | abs dT hot [K] | L1 OH | L1 CO | V(T>1500) xDI |
|---|---|---|---|---|---|---|---|---|---|
| flow only (chemistry off) | 1.32 | - | - | - | - | - | - | - | - |
| GA18 DI (seulex 1e-5/1e-10) | 13.63 | 12.31 | 63,087 | 781 | 1.0x | 0.00 | 0.0 % | 0.0 % | 1.000 |
| DI, Treact 600 K | 12.62 | 11.30 | 14,646 | 3086 | 1.1x | 0.26 | 0.0 % | 0.0 % | 1.000 |
| TDAC/ISAT tol 1e-3 | 2.92 | 1.60 | 63,087 | 101 | 7.7x | 1.41 | 1.5 % | 0.3 % | 1.003 |
| TDAC/ISAT tol 1e-4 | 3.73 | 2.41 | 63,087 | 153 | 5.1x | 0.85 | 0.4 % | 0.1 % | 1.000 |
| TDAC/ISAT tol 1e-5 | 6.89 | 5.57 | 63,087 | 353 | 2.2x | 0.67 | 0.2 % | 0.1 % | 0.999 |
| surrogate tix2h_s0 (pure) | 2.05 | 0.73 | 14,633 | 200 | 16.9x | 4.68 | 32.0 % | 5.7 % | 1.003 |
| surrogate P_mix, 6 members (pure) | 8.95 | 7.63 | 14,611 | 2089 | 1.6x | 3.08 | 18.9 % | 3.0 % | 1.000 |

## Findings

1. **Chemistry is about 90 % of a DI step** (12.3 of 13.6 s/step on 4 ranks); the flow solve with radiation is 1.3 s/step.
   It sets the floor for any chemistry speed-up (Amdahl): even free chemistry would make a step only about 10x faster.
2. **A temperature cutoff barely helps** (Treact 600 K: -8 %). The 48k cold cells cost about 1 s/step of DI; the 14.6k cells
   above 600 K carry the rest, about 3,100 CPU-us per hot cell-step.
3. **ISAT (TDAC, no reduction) is the strong baseline.** At tolerance 1e-4 chemistry is 5.1x faster than DI with abs dT 0.85 K
   and L1 OH 0.4 % after 200 steps; at 1e-3 it is 7.7x faster with 1.4 K. That is the "fair comparison" the reviewers will
   ask for (roadmap negative result 13).
4. **The single surrogate is the fastest chemistry** (tix2h_s0: 0.73 s/step, 16.9x DI, about 200 CPU-us per advanced cell,
   15x cheaper than DI per hot cell). It is also the least accurate: after 200 steps (4 ms) abs dT is 4.7 K and L1 OH 32 %.
   On the whole step that is 2.05 vs 2.92 s for ISAT 1e-3, i.e. only 1.4x faster than ISAT at 3x its temperature error.
5. **The 6-member ensemble P_mix is slower than ISAT at every tolerance** (7.6 s/step chemistry, 1.6x DI) and less accurate
   (3.1 K, L1 OH 19 %). Ensembles buy accuracy and stability in the long CFD run (protocol v2) at about 1 s/step per member.
6. **At matched accuracy ISAT wins on this case.** For the surrogate to pay off it must reach ISAT 1e-3's error (about 1.4 K
   over 4 ms) at its single-network cost. The C2/C3 work (ignition coverage, then ITERML) targets that accuracy gap.
   Ensembles of more than 2-3 members are not competitive on cost.

Caveats: two cases at a time plus C2's 8 threads on a 16-core VM, so absolute times carry load (all cases equally); 200
steps (4 ms) is short for ISAT, whose table keeps growing and retrieving better over a long run, and for surrogate error
growth (the protocol's 50 ms flame phase measures that: tix2h_s0 11.8 K, P_mix 10.3 K). The surrogates ran pure (no DI
fallback) with the shadow-DI checks on.
