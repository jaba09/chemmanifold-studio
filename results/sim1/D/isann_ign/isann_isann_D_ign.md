# ISANN isann_D_ign: 25.0 ms simulados

- Fase DI: 468 pasos; primera red en uso a 9.38 ms
- Coste: 7.85 s/paso en fase DI, 4.32 s/paso con red (x1.82)
- Fracción GA18 de celdas calientes: 38.2 % en total, 0.57 % en fase red
- Pares guardados al final (rejilla): 50389 de 21706732 candidatos

## Rondas de entrenamiento

| ronda | motivo | paso | pares online | replay | entrenamiento [s] | dT 1 paso cand / actual [K] | rollout cand / actual [K] | aceptada | versión |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 401 DI steps >= max_steps | 401 | 15405 | 46215 | 408 | 0.100 / 0.730 | 7.71 / 10.81 | sí | 1 |
| 2 | 1726 new pairs | 569 | 17131 | 51393 | 449 | 0.078 / 0.100 | 1.70 / 2.23 | sí | 2 |
| 3 | 7 untrusted bins | 785 | 18448 | 55344 | 503 | 0.067 / 0.079 | 7.17 / 9.83 | no | - |
| 4 | 7 untrusted bins | 939 | 19080 | 57240 | 490 | 0.067 / 0.080 | 1.78 / 1.90 | sí | 3 |
| 5 | 6 untrusted bins | 1182 | 19923 | 59769 | 354 | 0.067 / 0.067 | 5.96 / 5.96 | no | - |

## Por ventana

| t [ms] | versiones | GA18 | OOD | no fiable | s/paso | sombra mal |
|---|---|---|---|---|---|---|
| 0.0-2.5 | 0-0 | 100.00 % | 0.00 % | 0.00 % | 7.81 | 0.0 % |
| 2.5-5.0 | 0-0 | 100.00 % | 0.00 % | 0.00 % | 7.80 | 0.0 % |
| 5.0-7.5 | 0-0 | 100.00 % | 0.00 % | 0.00 % | 7.85 | 0.0 % |
| 7.5-10.0 | 0-1 | 74.46 % | 0.00 % | 0.04 % | 6.85 | 3.5 % |
| 10.0-12.5 | 1-1 | 0.54 % | 0.00 % | 0.54 % | 4.63 | 0.8 % |
| 12.5-15.0 | 1-2 | 0.54 % | 0.00 % | 0.54 % | 4.44 | 1.1 % |
| 15.0-17.5 | 2-2 | 0.56 % | 0.00 % | 0.56 % | 4.16 | 0.5 % |
| 17.5-20.0 | 2-2 | 0.69 % | 0.00 % | 0.69 % | 4.32 | 0.5 % |
| 20.0-22.5 | 2-3 | 0.62 % | 0.00 % | 0.62 % | 4.22 | 0.8 % |
| 22.5-25.0 | 3-3 | 0.59 % | 0.01 % | 0.58 % | 4.31 | 0.2 % |
