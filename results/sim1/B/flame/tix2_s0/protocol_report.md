# Protocolo CFD: tix2_s0

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2/08_fluent/resnet_film`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **23.2 K** (sesgo -19.1 K) |
| Deriva de ese error (100-150 ms) | +1.55 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 25.8 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 20.2 / 21.6 / 12.7 / 33.4 K |
| p95 abs dT, celdas calientes | 59 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 30 % / 31 %, ×1.27 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 16 % / 12 %, ×1.11 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 8 % / 14 %, ×0.93 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 62 % / 61 %, ×1.59 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.51 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 11 % |
| Error L1 del campo de calor liberado (celdas calientes) | 236 % |
| GA18 / OOD | 0.0 % / 8.7 % |
| Coste | 1.94 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 27015 (4294) | 0.0714 | 11 % | 11 % | 13 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4526 | 17.8 | -15.8 | 7.9 | 15.7 | 28 % | 7 % | 1.00 | 3.40 | 2123 / 2105 |
| 105.0 | llama | 4531 | 19.9 | -17.1 | 10.7 | 21.0 | 29 % | 9 % | 1.01 | 3.44 | 2123 / 2105 |
| 107.5 | llama | 4541 | 20.6 | -17.6 | 12.2 | 22.6 | 29 % | 10 % | 1.01 | 3.46 | 2123 / 2105 |
| 110.0 | llama | 4546 | 21.0 | -17.8 | 13.4 | 23.0 | 30 % | 11 % | 1.00 | 3.47 | 2123 / 2105 |
| 112.5 | llama | 4541 | 21.3 | -18.2 | 14.8 | 24.4 | 30 % | 12 % | 1.00 | 3.49 | 2123 / 2106 |
| 115.0 | llama | 4542 | 21.7 | -18.4 | 15.9 | 24.5 | 30 % | 13 % | 1.00 | 3.51 | 2123 / 2107 |
| 117.5 | llama | 4542 | 22.1 | -18.6 | 16.8 | 24.8 | 30 % | 14 % | 1.00 | 3.52 | 2123 / 2107 |
| 120.0 | llama | 4547 | 22.4 | -18.8 | 17.8 | 25.1 | 30 % | 15 % | 1.00 | 3.53 | 2123 / 2108 |
| 122.5 | llama | 4544 | 22.3 | -18.8 | 19.9 | 24.7 | 31 % | 16 % | 1.00 | 3.53 | 2123 / 2109 |
| 125.0 | llama | 4561 | 23.1 | -19.3 | 21.5 | 24.9 | 30 % | 18 % | 1.00 | 3.52 | 2123 / 2109 |
| 127.5 | llama | 4562 | 23.8 | -19.7 | 23.2 | 25.2 | 31 % | 18 % | 0.99 | 3.55 | 2123 / 2109 |
| 130.0 | llama | 4567 | 24.3 | -19.7 | 24.2 | 25.4 | 31 % | 19 % | 1.00 | 3.57 | 2123 / 2110 |
| 132.5 | llama | 4572 | 24.6 | -19.6 | 24.8 | 25.3 | 31 % | 19 % | 1.00 | 3.55 | 2123 / 2110 |
| 135.0 | llama | 4571 | 25.0 | -19.9 | 25.3 | 25.3 | 31 % | 19 % | 1.00 | 3.55 | 2123 / 2109 |
| 137.5 | llama | 4571 | 25.3 | -20.0 | 25.3 | 26.1 | 31 % | 20 % | 0.99 | 3.55 | 2122 / 2109 |
| 140.0 | llama | 4569 | 25.4 | -20.1 | 25.5 | 27.1 | 31 % | 19 % | 1.00 | 3.54 | 2122 / 2109 |
| 142.5 | llama | 4570 | 25.7 | -20.5 | 25.7 | 27.9 | 31 % | 19 % | 1.00 | 3.51 | 2122 / 2108 |
| 145.0 | llama | 4569 | 25.8 | -20.7 | 26.2 | 28.6 | 31 % | 20 % | 1.00 | 3.51 | 2121 / 2107 |
| 147.5 | llama | 4564 | 26.0 | -21.0 | 26.4 | 29.0 | 31 % | 20 % | 0.99 | 3.51 | 2121 / 2107 |
| 150.0 | llama | 4556 | 26.0 | -21.3 | 26.3 | 29.3 | 31 % | 20 % | 0.99 | 3.49 | 2121 / 2107 |
