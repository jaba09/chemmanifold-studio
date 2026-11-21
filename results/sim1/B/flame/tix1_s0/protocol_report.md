# Protocolo CFD: tix1_s0

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/tix1_s0`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **43.8 K** (sesgo -26.3 K) |
| Deriva de ese error (100-150 ms) | +0.56 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 43.4 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 25.9 / 20.0 / 12.4 / 28.0 K |
| p95 abs dT, celdas calientes | 91 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 26 % / 23 %, ×1.11 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 27 % / 18 %, ×0.75 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 10 %, ×1.06 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 125 % / 127 %, ×2.20 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×2.13 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 12 % |
| Error L1 del campo de calor liberado (celdas calientes) | 232 % |
| GA18 / OOD | 0.0 % / 14.1 % |
| Coste | 2.08 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 27015 (6836) | 0.087 | 15 % | 8 % | 17 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4554 | 33.6 | -21.5 | 13.7 | 22.4 | 26 % | 12 % | 1.01 | 2.10 | 2123 / 2070 |
| 105.0 | llama | 4625 | 38.7 | -23.1 | 18.3 | 27.7 | 25 % | 19 % | 1.01 | 2.12 | 2123 / 2065 |
| 107.5 | llama | 4667 | 41.9 | -24.4 | 22.2 | 30.9 | 25 % | 24 % | 1.01 | 2.16 | 2123 / 2060 |
| 110.0 | llama | 4711 | 44.3 | -25.0 | 25.4 | 33.1 | 26 % | 28 % | 1.01 | 2.19 | 2123 / 2055 |
| 112.5 | llama | 4732 | 45.9 | -25.7 | 27.2 | 34.4 | 26 % | 30 % | 1.01 | 2.22 | 2123 / 2052 |
| 115.0 | llama | 4732 | 46.4 | -26.8 | 27.6 | 35.1 | 26 % | 31 % | 1.00 | 2.23 | 2123 / 2050 |
| 117.5 | llama | 4721 | 46.3 | -27.9 | 27.7 | 35.4 | 26 % | 30 % | 1.00 | 2.23 | 2123 / 2049 |
| 120.0 | llama | 4722 | 46.2 | -28.2 | 27.8 | 35.5 | 26 % | 30 % | 1.00 | 2.23 | 2123 / 2049 |
| 122.5 | llama | 4720 | 46.1 | -28.1 | 27.8 | 35.6 | 26 % | 30 % | 1.00 | 2.21 | 2123 / 2050 |
| 125.0 | llama | 4725 | 45.9 | -27.7 | 27.8 | 35.9 | 26 % | 29 % | 0.99 | 2.19 | 2123 / 2050 |
| 127.5 | llama | 4726 | 45.7 | -27.2 | 27.8 | 36.2 | 26 % | 29 % | 0.99 | 2.17 | 2123 / 2051 |
| 130.0 | llama | 4723 | 45.0 | -27.1 | 27.5 | 36.3 | 26 % | 28 % | 0.99 | 2.14 | 2123 / 2051 |
| 132.5 | llama | 4705 | 44.5 | -27.2 | 27.0 | 36.9 | 27 % | 28 % | 0.99 | 2.12 | 2123 / 2051 |
| 135.0 | llama | 4693 | 44.2 | -27.3 | 26.7 | 37.4 | 27 % | 28 % | 0.99 | 2.09 | 2123 / 2052 |
| 137.5 | llama | 4691 | 44.0 | -27.2 | 26.8 | 37.8 | 27 % | 28 % | 0.99 | 2.07 | 2122 / 2054 |
| 140.0 | llama | 4692 | 44.0 | -27.1 | 27.0 | 38.2 | 26 % | 28 % | 0.99 | 2.05 | 2122 / 2055 |
| 142.5 | llama | 4699 | 44.1 | -26.7 | 27.3 | 38.4 | 26 % | 28 % | 0.99 | 2.02 | 2122 / 2055 |
| 145.0 | llama | 4702 | 43.9 | -26.3 | 27.5 | 38.4 | 26 % | 28 % | 0.99 | 2.00 | 2121 / 2055 |
| 147.5 | llama | 4700 | 43.2 | -25.7 | 27.5 | 37.7 | 26 % | 27 % | 0.99 | 2.02 | 2121 / 2055 |
| 150.0 | llama | 4695 | 41.6 | -24.8 | 27.1 | 36.0 | 26 % | 27 % | 0.99 | 2.11 | 2121 / 2054 |
