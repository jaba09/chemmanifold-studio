# C3b decisions (ITERML v2b: 20 % seeded share, repeats from scratch)

Settings frozen before the start: `configs/iterml/iterml_v2b_tix2c.yaml` (copy of C3's `iterml_v2_tix2h.yaml`).
Javier's choice (17 Nov): "ITERML variant: 20% seeds, fresh".

- 17 Nov 23:20 CET, setup:
  - `seeded.max_share` 0.20 (C3: 0.35). The cap is applied in the seeded exploration (stage 4,
    `chemmanifold/seeded.py`), so C3's `pairs_seeded_iter{1,2}.npz` (35 %, 405,184 pairs) are NOT reused; the
    exploration is re-run from the reused seeds (cap 0.25 x 752,486 a-priori pairs = 188,121 seeded pairs).
  - Training: the 3 repeats (s0, s1, s2; seeds base+k, +100, +200) from scratch on the full set (a-priori tix2c pairs
    + seeded pairs) with the tix2c recipe (300 epochs, lr_max 2e-3, rollout loss, latent 12, tix2c scalers), no
    `init_from`; 3/3/2 threads in parallel (8 cores), `07_train.py --resume`.
  - Iteration 0 = P_tix2c (S 2.00: F 1.60, I 2.00, C 0.15). Accept if ensemble S < best x 0.9; stop after 2
    rejections in a row or 6 iterations; protocol v2 on the mean ensemble.
  - Reuse (allowed by the frozen rules because the collection and seeds depend only on the parent's member 0 and
    the seed lineage): iteration 1 reuses C3 iteration 1's collection legs (symlinks) and 11,440 seeds (copy);
    iteration 2 reuses C3 iteration 2's, but only if it starts from iteration 0 (C3b iteration 1 rejected). If
    iteration 1 is accepted, iteration 2 collects with C3b_iter1 member 0. Iterations 3+ collect anew.
  - Root `/opt/ofb/iterml_v2b`, systemd user unit `sim1-c3b`; GRI units untouched.
  - Disk rule: below 15 GB free, trim C3's collection runs' field data (seeds and logs kept).

## Loop log (from /opt/ofb/iterml_v2b/DECISIONS.md)

- 2026-11-17 23:23 CET: baseline: iteration 0 = P_tix2c (ensemble) S = 2.00 (F 1.60, I 2.00, C 0.15)
- 2026-11-17 23:23 CET: iteration 1 starts from iteration 0 (the best, S 2.00)
