# A2: ignition DI reference (corrected case, LeFoam + constantLewis)

Run 9 Nov 23:11 to 10 Nov 01:52 CET, 4 ranks, 7.2-7.7 s/step. Start: protocol lean start (phi 0.5 burnt gas, 1480 K,
in fff-fluid-fuel + fff-fluid-mixing; air 300 K at rest elsewhere) on the corrected mesh. GA18 DI (seulex 1e-5/1e-10),
Euler, dt 2e-5 s, 0-25 ms. Writes every 0.5 ms to 5 ms, then every 2.5 ms (18 snapshots; CSVs in
/opt/ofb/runs/A2_ign/snap, made with foam_snapshot.py for score_protocol.py).

- Ignition time (first domain Tmax > 1600 K, minMaxT sampled every 0.2 ms): **2.4 ms**
- Domain Tmax (K):

| t (ms) | Tmax (K) |
|---|---|
| 1.0 | 1480 |
| 2.0 | 1480 |
| 3.0 | 2055 |
| 4.0 | 2089 |
| 5.0 | 2098 |
| 10.0 | 2119 |
| 15.0 | 2127 |
| 20.0 | 2131 |
| 25.0 | 2134 |
