# Protocolo CFD: P_tix2

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | – / 100.20 / – ms |
| Máximo exceso de Tmax del dominio sobre DI | – K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +0 K |
| Media abs dT en la llama | 0.0 K |
| Media abs dT en la boquilla | 0.0 K |
| Media abs dT, celdas calientes | 0.0 K |
| Error L1 de OH, celdas calientes | 0 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **24.2 K** (sesgo -19.5 K) |
| Deriva de ese error (100-150 ms) | +1.67 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 26.8 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 12.9 / 7.7 / 7.4 / 10.8 K |
| p95 abs dT, celdas calientes | 39 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 24 % / 24 %, ×1.23 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 11 % / 10 %, ×1.09 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 5 % / 10 %, ×0.95 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 70 % / 68 %, ×1.69 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×2.52 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 10 % |
| Error L1 del campo de calor liberado (celdas calientes) | 179 % |
| GA18 / OOD | 0.0 % / 3.6 % |
| Coste | 3.05 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 18488 (1752) | 0.0325 | 6 % | 12 % | 10 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4521 | 17.1 | -15.7 | 7.4 | 13.9 | 21 % | 5 % | 1.00 | 2.51 | 2123 / 2104 |
| 105.0 | llama | 4531 | 19.9 | -17.6 | 9.2 | 16.3 | 22 % | 7 % | 1.00 | 2.53 | 2123 / 2104 |
| 107.5 | llama | 4539 | 21.2 | -18.4 | 10.2 | 17.3 | 22 % | 9 % | 1.00 | 2.55 | 2123 / 2104 |
| 110.0 | llama | 4541 | 21.9 | -18.6 | 11.2 | 18.5 | 23 % | 10 % | 1.00 | 2.55 | 2123 / 2105 |
| 112.5 | llama | 4547 | 22.5 | -18.8 | 11.7 | 18.7 | 23 % | 10 % | 1.00 | 2.56 | 2123 / 2106 |
| 115.0 | llama | 4550 | 23.1 | -18.9 | 12.0 | 18.6 | 24 % | 11 % | 1.00 | 2.56 | 2123 / 2106 |
| 117.5 | llama | 4551 | 23.6 | -19.0 | 12.4 | 19.0 | 24 % | 11 % | 1.01 | 2.56 | 2123 / 2106 |
| 120.0 | llama | 4562 | 23.9 | -19.1 | 12.7 | 19.0 | 24 % | 12 % | 1.01 | 2.56 | 2123 / 2106 |
| 122.5 | llama | 4560 | 24.2 | -19.1 | 13.0 | 18.9 | 24 % | 12 % | 1.01 | 2.55 | 2123 / 2106 |
| 125.0 | llama | 4573 | 24.5 | -19.1 | 13.2 | 19.0 | 24 % | 12 % | 1.00 | 2.55 | 2123 / 2106 |
| 127.5 | llama | 4578 | 24.9 | -19.2 | 13.4 | 19.2 | 24 % | 12 % | 1.00 | 2.55 | 2123 / 2106 |
| 130.0 | llama | 4580 | 25.3 | -19.4 | 13.6 | 19.5 | 24 % | 13 % | 1.00 | 2.55 | 2123 / 2106 |
| 132.5 | llama | 4580 | 25.6 | -19.6 | 13.8 | 19.7 | 24 % | 13 % | 1.01 | 2.54 | 2123 / 2105 |
| 135.0 | llama | 4584 | 25.9 | -19.7 | 14.0 | 19.9 | 24 % | 13 % | 1.01 | 2.53 | 2123 / 2105 |
| 137.5 | llama | 4582 | 26.2 | -20.0 | 14.1 | 20.0 | 24 % | 12 % | 1.01 | 2.51 | 2122 / 2104 |
| 140.0 | llama | 4579 | 26.4 | -20.4 | 14.3 | 20.3 | 24 % | 12 % | 1.01 | 2.49 | 2122 / 2103 |
| 142.5 | llama | 4579 | 26.6 | -20.8 | 14.6 | 20.7 | 24 % | 12 % | 1.01 | 2.48 | 2122 / 2102 |
| 145.0 | llama | 4575 | 26.7 | -21.4 | 15.1 | 21.4 | 24 % | 11 % | 1.00 | 2.46 | 2121 / 2102 |
| 147.5 | llama | 4569 | 26.9 | -22.0 | 15.7 | 22.0 | 24 % | 11 % | 1.00 | 2.45 | 2121 / 2101 |
| 150.0 | llama | 4561 | 27.1 | -22.7 | 16.2 | 22.5 | 23 % | 11 % | 1.00 | 2.45 | 2121 / 2101 |
