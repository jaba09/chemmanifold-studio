# Protocolo CFD: isann_arc22b

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
| **Media abs dT en la llama** (T > 1600 K) | **31.9 K** (sesgo -31.1 K) |
| Deriva de ese error (100-150 ms) | +0.85 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 31.4 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 21.3 / 18.8 / 14.3 / 12.4 K |
| p95 abs dT, celdas calientes | 61 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 14 % / 13 %, ×1.06 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 12 % / 10 %, ×0.94 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 12 % / 30 %, ×0.88 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 32 % / 31 %, ×1.26 |
| Volumen por encima de 1500 K, modelo/DI | ×0.97 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.01 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 6 % |
| Error L1 del campo de calor liberado (celdas calientes) | 33 % |
| GA18 / OOD | – / – |
| Coste | 6.47 s por paso (None procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 75132 (0) | 0.044 | 8 % | 6 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 0.93 | 2123 / 2123 |
| 102.5 | llama | 4505 | 24.1 | -24.1 | 10.1 | 16.3 | 7 % | 1 % | 0.99 | 0.95 | 2123 / 2114 |
| 105.0 | llama | 4509 | 27.9 | -27.8 | 13.4 | 21.3 | 8 % | 3 % | 0.98 | 0.94 | 2123 / 2114 |
| 107.5 | llama | 4511 | 29.8 | -29.7 | 15.9 | 24.8 | 9 % | 4 % | 0.97 | 0.94 | 2123 / 2114 |
| 110.0 | llama | 4513 | 28.6 | -28.5 | 16.4 | 24.8 | 10 % | 6 % | 0.97 | 0.90 | 2123 / 2115 |
| 112.5 | llama | 4515 | 30.5 | -30.4 | 18.1 | 26.2 | 11 % | 10 % | 0.97 | 0.98 | 2123 / 2112 |
| 115.0 | llama | 4520 | 32.4 | -32.3 | 20.6 | 27.4 | 12 % | 12 % | 0.97 | 0.96 | 2123 / 2110 |
| 117.5 | llama | 4520 | 33.5 | -33.4 | 22.5 | 27.7 | 13 % | 12 % | 0.97 | 0.97 | 2123 / 2110 |
| 120.0 | llama | 4526 | 34.2 | -34.1 | 23.8 | 27.7 | 14 % | 12 % | 0.97 | 0.97 | 2123 / 2110 |
| 122.5 | llama | 4520 | 34.7 | -34.5 | 24.9 | 27.8 | 14 % | 13 % | 0.96 | 0.97 | 2123 / 2110 |
| 125.0 | llama | 4534 | 34.6 | -34.2 | 25.3 | 27.7 | 15 % | 13 % | 0.96 | 0.97 | 2123 / 2111 |
| 127.5 | llama | 4539 | 34.4 | -33.8 | 25.4 | 27.6 | 15 % | 14 % | 0.96 | 0.97 | 2123 / 2112 |
| 130.0 | llama | 4546 | 34.2 | -33.5 | 25.5 | 27.5 | 15 % | 16 % | 0.97 | 0.96 | 2123 / 2112 |
| 132.5 | llama | 4550 | 34.2 | -33.5 | 25.4 | 27.2 | 15 % | 16 % | 0.97 | 0.96 | 2123 / 2111 |
| 135.0 | llama | 4551 | 34.1 | -33.4 | 25.2 | 26.9 | 15 % | 16 % | 0.97 | 0.96 | 2123 / 2111 |
| 137.5 | llama | 4550 | 34.2 | -33.5 | 25.2 | 27.1 | 16 % | 16 % | 0.97 | 1.21 | 2122 / 2110 |
| 140.0 | llama | 4556 | 31.8 | -30.5 | 23.4 | 25.0 | 16 % | 14 % | 0.98 | 1.11 | 2122 / 2112 |
| 142.5 | llama | 4561 | 31.5 | -29.6 | 22.8 | 23.9 | 17 % | 14 % | 0.98 | 1.14 | 2122 / 2112 |
| 145.0 | llama | 4556 | 31.3 | -28.9 | 21.6 | 23.2 | 18 % | 15 % | 0.99 | 1.17 | 2121 / 2112 |
| 147.5 | llama | 4555 | 31.1 | -28.4 | 20.5 | 22.4 | 17 % | 15 % | 0.99 | 1.10 | 2121 / 2111 |
| 150.0 | llama | 4555 | 31.1 | -28.1 | 19.8 | 21.9 | 17 % | 15 % | 0.99 | 1.09 | 2121 / 2109 |
