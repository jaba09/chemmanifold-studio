# Protocolo CFD: tix2h_s2

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2h_seeds/s2/08_fluent/resnet_film`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **52.9 K** (sesgo -22.2 K) |
| Deriva de ese error (100-150 ms) | +11.43 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 70.3 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 91.1 / 117.9 / 81.0 / 197.3 K |
| p95 abs dT, celdas calientes | 331 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 63 % / 57 %, ×1.55 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 61 % / 34 %, ×1.51 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 32 % / 47 %, ×0.72 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 113 % / 100 %, ×2.06 |
| Volumen por encima de 1500 K, modelo/DI | ×0.96 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×4.93 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / -7 % |
| Error L1 del campo de calor liberado (celdas calientes) | 458 % |
| GA18 / OOD | 0.0 % / 24.1 % |
| Coste | 2.04 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 28826 (9523) | 0.273 | 33 % | 23 % | 11 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4513 | 15.7 | -15.1 | 7.2 | 12.6 | 31 % | 5 % | 1.00 | 4.31 | 2123 / 2093 |
| 105.0 | llama | 4530 | 17.6 | -16.2 | 12.4 | 24.3 | 36 % | 8 % | 0.99 | 4.17 | 2123 / 2091 |
| 107.5 | llama | 4548 | 27.7 | -24.3 | 29.7 | 61.0 | 41 % | 23 % | 0.96 | 4.39 | 2123 / 2090 |
| 110.0 | llama | 4525 | 45.9 | -40.9 | 58.8 | 81.3 | 49 % | 56 % | 0.91 | 5.24 | 2123 / 2092 |
| 112.5 | llama | 4537 | 39.1 | -27.9 | 65.7 | 88.2 | 54 % | 66 % | 0.93 | 5.50 | 2123 / 2106 |
| 115.0 | llama | 4558 | 37.5 | -18.8 | 66.2 | 88.0 | 56 % | 64 % | 0.94 | 5.18 | 2123 / 2115 |
| 117.5 | llama | 4568 | 42.9 | -18.7 | 71.2 | 90.4 | 58 % | 68 % | 0.95 | 5.19 | 2123 / 2119 |
| 120.0 | llama | 4591 | 47.3 | -18.5 | 77.6 | 94.0 | 61 % | 69 % | 0.95 | 5.14 | 2123 / 2123 |
| 122.5 | llama | 4614 | 52.4 | -18.8 | 88.2 | 99.2 | 64 % | 72 % | 0.95 | 5.14 | 2123 / 2127 |
| 125.0 | llama | 4654 | 57.1 | -18.4 | 98.3 | 105.6 | 67 % | 71 % | 0.96 | 5.09 | 2123 / 2129 |
| 127.5 | llama | 4672 | 60.3 | -18.9 | 106.0 | 110.4 | 69 % | 73 % | 0.96 | 5.05 | 2123 / 2129 |
| 130.0 | llama | 4678 | 62.7 | -19.5 | 112.4 | 114.6 | 71 % | 72 % | 0.97 | 5.00 | 2123 / 2128 |
| 132.5 | llama | 4677 | 65.1 | -21.3 | 117.6 | 117.3 | 73 % | 74 % | 0.97 | 5.00 | 2123 / 2126 |
| 135.0 | llama | 4675 | 66.8 | -22.2 | 121.5 | 118.7 | 74 % | 73 % | 0.97 | 4.97 | 2123 / 2124 |
| 137.5 | llama | 4662 | 68.0 | -23.2 | 125.4 | 119.6 | 75 % | 73 % | 0.97 | 4.96 | 2122 / 2121 |
| 140.0 | llama | 4661 | 69.1 | -23.8 | 128.8 | 119.3 | 76 % | 72 % | 0.98 | 4.91 | 2122 / 2119 |
| 142.5 | llama | 4655 | 70.4 | -25.1 | 131.9 | 118.3 | 76 % | 72 % | 0.98 | 4.86 | 2122 / 2118 |
| 145.0 | llama | 4647 | 70.7 | -24.7 | 133.8 | 116.8 | 78 % | 71 % | 0.97 | 4.92 | 2121 / 2119 |
| 147.5 | llama | 4641 | 70.5 | -23.9 | 134.6 | 115.1 | 78 % | 69 % | 0.97 | 4.88 | 2121 / 2118 |
| 150.0 | llama | 4611 | 70.6 | -24.3 | 134.8 | 113.9 | 78 % | 68 % | 0.97 | 4.80 | 2121 / 2117 |
