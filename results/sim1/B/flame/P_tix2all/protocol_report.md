# Protocolo CFD: P_tix2all

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2all`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **22.3 K** (sesgo -18.1 K) |
| Deriva de ese error (100-150 ms) | +1.33 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 24.7 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 14.5 / 10.1 / 8.1 / 33.2 K |
| p95 abs dT, celdas calientes | 45 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 27 % / 28 %, ×1.24 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 14 % / 10 %, ×1.12 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 15 %, ×0.91 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 56 % / 54 %, ×1.53 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.92 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 35 % |
| Error L1 del campo de calor liberado (celdas calientes) | 315 % |
| GA18 / OOD | 0.0 % / 3.5 % |
| Coste | 4.02 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 24194 (2167) | 0.0357 | 6 % | 14 % | 8 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4518 | 17.0 | -15.6 | 7.4 | 14.3 | 23 % | 5 % | 1.00 | 3.97 | 2123 / 2105 |
| 105.0 | llama | 4529 | 19.2 | -16.8 | 9.3 | 17.3 | 24 % | 7 % | 1.00 | 3.98 | 2123 / 2105 |
| 107.5 | llama | 4535 | 20.1 | -17.2 | 10.5 | 19.3 | 25 % | 8 % | 1.00 | 3.97 | 2123 / 2106 |
| 110.0 | llama | 4540 | 20.6 | -17.3 | 11.5 | 21.0 | 26 % | 9 % | 1.00 | 3.97 | 2123 / 2106 |
| 112.5 | llama | 4539 | 21.0 | -17.3 | 12.3 | 22.3 | 26 % | 10 % | 1.00 | 3.96 | 2123 / 2106 |
| 115.0 | llama | 4544 | 21.4 | -17.3 | 12.6 | 22.1 | 27 % | 10 % | 1.00 | 3.95 | 2123 / 2107 |
| 117.5 | llama | 4544 | 21.7 | -17.4 | 12.9 | 21.8 | 27 % | 11 % | 1.00 | 3.95 | 2123 / 2107 |
| 120.0 | llama | 4547 | 22.0 | -17.5 | 13.2 | 21.7 | 27 % | 12 % | 1.01 | 3.94 | 2123 / 2107 |
| 122.5 | llama | 4545 | 22.2 | -17.6 | 13.7 | 22.4 | 28 % | 12 % | 1.00 | 3.94 | 2123 / 2107 |
| 125.0 | llama | 4557 | 22.4 | -17.7 | 14.3 | 23.4 | 28 % | 13 % | 1.00 | 3.93 | 2123 / 2107 |
| 127.5 | llama | 4559 | 22.6 | -17.8 | 14.8 | 24.2 | 28 % | 14 % | 1.00 | 3.92 | 2123 / 2107 |
| 130.0 | llama | 4566 | 22.8 | -17.9 | 15.0 | 24.1 | 28 % | 15 % | 1.00 | 3.91 | 2123 / 2107 |
| 132.5 | llama | 4569 | 23.1 | -18.1 | 15.4 | 24.0 | 28 % | 16 % | 1.00 | 3.91 | 2123 / 2107 |
| 135.0 | llama | 4567 | 23.3 | -18.4 | 16.0 | 24.6 | 28 % | 17 % | 1.00 | 3.90 | 2123 / 2107 |
| 137.5 | llama | 4563 | 23.6 | -18.7 | 16.6 | 25.6 | 28 % | 18 % | 1.00 | 3.89 | 2122 / 2107 |
| 140.0 | llama | 4564 | 24.0 | -19.0 | 17.3 | 26.7 | 28 % | 19 % | 1.00 | 3.88 | 2122 / 2106 |
| 142.5 | llama | 4566 | 24.4 | -19.4 | 18.1 | 27.9 | 28 % | 20 % | 1.00 | 3.87 | 2122 / 2106 |
| 145.0 | llama | 4563 | 24.7 | -19.8 | 18.8 | 29.0 | 28 % | 21 % | 0.99 | 3.87 | 2121 / 2105 |
| 147.5 | llama | 4559 | 25.0 | -20.2 | 19.5 | 30.0 | 29 % | 22 % | 0.99 | 3.87 | 2121 / 2105 |
| 150.0 | llama | 4553 | 25.3 | -20.5 | 20.2 | 30.7 | 29 % | 23 % | 0.99 | 3.87 | 2121 / 2105 |
