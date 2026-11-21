# Protocolo CFD: arc22_flame

Modo: **di**. Modelo: `GA18 (DI)`. Estado: failed 0.185 (hasta 150.0 ms). Puntuación **no válida** (no llega a 150 ms).

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
| **Media abs dT en la llama** (T > 1600 K) | **33.3 K** (sesgo -33.0 K) |
| Deriva de ese error (100-150 ms) | +1.96 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 36.2 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 23.5 / 21.7 / 15.3 / 21.6 K |
| p95 abs dT, celdas calientes | 61 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 13 % / 13 %, ×1.05 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 9 %, ×0.93 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 13 % / 32 %, ×0.87 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 28 % / 27 %, ×1.20 |
| Volumen por encima de 1500 K, modelo/DI | ×0.97 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.93 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 6 % |
| Error L1 del campo de calor liberado (celdas calientes) | 28 % |
| GA18 / OOD | – / – |
| Coste | 11.15 s por paso (8 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 0.93 | 2123 / 2123 |
| 102.5 | llama | 4505 | 24.1 | -24.1 | 10.1 | 16.4 | 7 % | 1 % | 0.99 | 0.95 | 2123 / 2114 |
| 105.0 | llama | 4509 | 27.9 | -27.8 | 13.4 | 21.3 | 8 % | 3 % | 0.98 | 0.94 | 2123 / 2114 |
| 107.5 | llama | 4511 | 29.8 | -29.7 | 15.9 | 24.8 | 9 % | 4 % | 0.97 | 0.94 | 2123 / 2114 |
| 110.0 | llama | 4513 | 30.8 | -30.8 | 17.9 | 27.5 | 10 % | 5 % | 0.97 | 0.94 | 2123 / 2113 |
| 112.5 | llama | 4515 | 31.6 | -31.5 | 19.6 | 29.7 | 10 % | 5 % | 0.97 | 0.93 | 2123 / 2113 |
| 115.0 | llama | 4521 | 32.2 | -32.1 | 21.1 | 31.6 | 11 % | 6 % | 0.97 | 0.93 | 2123 / 2113 |
| 117.5 | llama | 4519 | 32.7 | -32.5 | 22.3 | 33.1 | 12 % | 7 % | 0.97 | 0.93 | 2123 / 2112 |
| 120.0 | llama | 4526 | 33.2 | -33.0 | 23.5 | 34.5 | 12 % | 7 % | 0.97 | 0.93 | 2123 / 2112 |
| 122.5 | llama | 4522 | 33.6 | -33.4 | 24.4 | 35.5 | 13 % | 7 % | 0.96 | 0.93 | 2123 / 2112 |
| 125.0 | llama | 4537 | 34.1 | -33.7 | 25.3 | 36.3 | 13 % | 8 % | 0.96 | 0.93 | 2123 / 2111 |
| 127.5 | llama | 4541 | 34.4 | -34.1 | 25.9 | 37.0 | 14 % | 8 % | 0.96 | 0.93 | 2123 / 2111 |
| 130.0 | llama | 4545 | 34.8 | -34.4 | 26.5 | 37.4 | 14 % | 8 % | 0.96 | 0.93 | 2123 / 2110 |
| 132.5 | llama | 4546 | 35.1 | -34.7 | 27.0 | 37.7 | 14 % | 9 % | 0.96 | 0.92 | 2123 / 2109 |
| 135.0 | llama | 4549 | 35.4 | -35.0 | 27.4 | 37.9 | 15 % | 9 % | 0.96 | 0.92 | 2123 / 2109 |
| 137.5 | llama | 4547 | 35.7 | -35.2 | 27.8 | 38.0 | 15 % | 9 % | 0.96 | 0.92 | 2122 / 2108 |
| 140.0 | llama | 4547 | 35.9 | -35.4 | 28.0 | 38.0 | 15 % | 9 % | 0.96 | 0.92 | 2122 / 2108 |
| 142.5 | llama | 4551 | 36.0 | -35.6 | 28.2 | 38.1 | 15 % | 9 % | 0.96 | 0.92 | 2122 / 2108 |
| 145.0 | llama | 4546 | 36.2 | -35.7 | 28.4 | 38.1 | 15 % | 10 % | 0.96 | 0.92 | 2121 / 2107 |
| 147.5 | llama | 4542 | 36.3 | -35.9 | 28.5 | 38.0 | 15 % | 10 % | 0.96 | 0.92 | 2121 / 2107 |
| 150.0 | llama | 4536 | 36.4 | -36.0 | 28.6 | 37.9 | 15 % | 10 % | 0.96 | 0.92 | 2121 / 2106 |
