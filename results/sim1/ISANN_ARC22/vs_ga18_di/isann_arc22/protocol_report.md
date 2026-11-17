# Protocolo CFD: isann_arc22

Modo: **di**. Modelo: `GA18 (DI)`. Estado: running (hasta 150.0 ms). Puntuación **no válida** (no llega a 150 ms).

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
| **Media abs dT en la llama** (T > 1600 K) | **34.2 K** (sesgo -33.7 K) |
| Deriva de ese error (100-150 ms) | +1.29 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 38.4 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 33.8 / 38.1 / 26.2 / 42.5 K |
| p95 abs dT, celdas calientes | 96 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 17 %, ×1.05 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 14 % / 12 %, ×0.99 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 17 % / 36 %, ×0.83 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 32 % / 31 %, ×1.20 |
| Volumen por encima de 1500 K, modelo/DI | ×0.96 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.93 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 6 % |
| Error L1 del campo de calor liberado (celdas calientes) | 43 % |
| GA18 / OOD | – / – |
| Coste | 5.87 s por paso (None procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 95133 (0) | 0.0728 | 10 % | 5 % | 4 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 0.93 | 2123 / 2123 |
| 102.5 | llama | 4505 | 24.1 | -24.1 | 10.1 | 16.3 | 7 % | 1 % | 0.99 | 0.95 | 2123 / 2114 |
| 105.0 | llama | 4509 | 27.9 | -27.8 | 13.4 | 21.3 | 8 % | 3 % | 0.98 | 0.94 | 2123 / 2114 |
| 107.5 | llama | 4511 | 42.5 | -42.4 | 24.5 | 35.3 | 17 % | 16 % | 0.95 | 0.91 | 2123 / 2113 |
| 110.0 | llama | 4513 | 42.4 | -42.3 | 29.7 | 38.0 | 23 % | 15 % | 0.94 | 0.87 | 2123 / 2111 |
| 112.5 | llama | 4515 | 34.5 | -34.4 | 26.6 | 33.9 | 18 % | 12 % | 0.95 | 0.89 | 2123 / 2113 |
| 115.0 | llama | 4520 | 31.8 | -31.7 | 24.4 | 33.3 | 17 % | 11 % | 0.95 | 0.89 | 2123 / 2114 |
| 117.5 | llama | 4518 | 31.4 | -31.4 | 26.4 | 36.4 | 18 % | 12 % | 0.96 | 0.87 | 2123 / 2114 |
| 120.0 | llama | 4525 | 32.1 | -32.1 | 28.7 | 38.3 | 18 % | 12 % | 0.96 | 0.86 | 2123 / 2113 |
| 122.5 | llama | 4519 | 32.2 | -32.1 | 30.7 | 38.4 | 16 % | 11 % | 0.96 | 0.95 | 2123 / 2113 |
| 125.0 | llama | 4534 | 31.7 | -31.3 | 31.7 | 36.9 | 16 % | 11 % | 0.96 | 0.95 | 2123 / 2113 |
| 127.5 | llama | 4542 | 31.6 | -30.6 | 33.2 | 36.6 | 17 % | 12 % | 0.96 | 0.96 | 2123 / 2113 |
| 130.0 | llama | 4550 | 31.7 | -30.4 | 35.0 | 37.3 | 18 % | 13 % | 0.97 | 0.96 | 2123 / 2112 |
| 132.5 | llama | 4554 | 31.9 | -30.6 | 36.8 | 39.3 | 18 % | 13 % | 0.97 | 0.92 | 2123 / 2112 |
| 135.0 | llama | 4552 | 32.4 | -31.2 | 38.5 | 43.6 | 19 % | 13 % | 0.97 | 0.87 | 2123 / 2112 |
| 137.5 | llama | 4550 | 33.5 | -32.9 | 40.3 | 49.2 | 20 % | 14 % | 0.96 | 0.90 | 2122 / 2112 |
| 140.0 | llama | 4543 | 34.8 | -34.6 | 41.4 | 53.9 | 21 % | 15 % | 0.96 | 0.92 | 2122 / 2111 |
| 142.5 | llama | 4546 | 36.5 | -36.2 | 44.4 | 60.7 | 21 % | 19 % | 0.95 | 0.95 | 2122 / 2111 |
| 145.0 | llama | 4541 | 38.7 | -38.1 | 48.9 | 67.6 | 22 % | 24 % | 0.94 | 0.95 | 2121 / 2112 |
| 147.5 | llama | 4540 | 41.2 | -40.0 | 55.2 | 69.3 | 23 % | 29 % | 0.93 | 1.08 | 2121 / 2115 |
| 150.0 | llama | 4536 | 40.6 | -38.8 | 56.5 | 63.7 | 22 % | 27 % | 0.93 | 1.05 | 2121 / 2119 |
