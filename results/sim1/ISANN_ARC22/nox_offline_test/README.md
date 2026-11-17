# Offline NOx test (17 Nov 2026, 23:30 CET)

Round 7 of the ISANN ARC22 run 1 (`/opt/ofb/run/isann_arc22/isann/round7`: 71 102 online + 60 000 replay pairs)
retrained from its accepted network v6, 20 epochs, warm start, as the daemon does:

- A: the same loss as run 1 (early stop at epoch 13: no validation improvement since epoch 0, so A = v6)
- B: + 07_train's relative species term (`training.radical_loss`, weight 0.1) on OH, H, O, HO2, NO, NO2, N2O, HCN

Evaluated on the run's 13 676 held-out online pairs (ARC DI, never trained on) and on 120 0D rollouts of 2 ms
(100 steps) from them against the ARC kernel (`evaluate.py`; one-step <s>_rel = median |error| / (|true increment|
+ 1e-3 Y + 1e-9); roll_<s> = median |error| / (Y_ARC + floor), floors OH 5e-5, NO 3e-6, NO2 2e-7, N2O 5e-8, HCN 2e-6).

| metric | v6 (= A) | B (NOx term) | change |
|---|---|---|---|
| one-step T MAE / p95 [K] | 0.080 / 0.309 | 0.074 / 0.283 | -8 % |
| one-step OH / CO / H | 0.426 / 0.384 / 0.112 | 0.264 / 0.350 / 0.116 | OH -38 % |
| one-step NO / NO2 / N2O / HCN | 0.215 / 0.454 / 0.132 / 0.150 | 0.183 / 0.219 / 0.105 / 0.082 | -15 / -52 / -21 / -45 % |
| rollout T mean / median / p95 [K] | 11.6 / 2.42 / 32.6 | 10.0 / 3.15 / 58.9 | mean -13 %, median +30 %, p95 x1.8 |
| rollouts with abs dT > 20 K | 13 | 17 | +4 |
| rollout NO / NO2 / N2O / HCN | 0.069 / 0.144 / 0.107 / 0.028 | 0.067 / 0.188 / 0.089 / 0.018 | NO2 +30 % |

The NOx term roughly halves the one-step NO2 and HCN errors and lowers NO by 15 %, but costs closed-loop T (more
failed rollouts). Run 2's gate would reject B on the rollout rule (17 > 13 failures; median above 1.1 x), so the
gate protects against that trade-off. The 2 ms rollouts see only ~7 % NO error while the CFD's hot-cell NO drifted to
48-76 % L1 over 50 ms: NO's slow (thermal) chemistry needs longer checks to show the drift.
