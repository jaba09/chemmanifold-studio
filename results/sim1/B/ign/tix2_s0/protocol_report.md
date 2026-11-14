# Protocolo CFD: tix2_s0

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2/08_fluent/resnet_film`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.40 / -1.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +406 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +337 K |
| Media abs dT en la llama | 146.4 K |
| Media abs dT en la boquilla | 5.1 K |
| Media abs dT, celdas calientes | 0.9 K |
| Error L1 de OH, celdas calientes | 98 % |
| GA18 / OOD | 0.0 % / 5.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **15.6 K** (sesgo -14.5 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.9 / 17.7 / 1.1 / 22.8 K |
| p95 abs dT, celdas calientes | 8 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 72 % / 30 %, ×0.38 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 22 % / 13 %, ×1.19 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 16 %, ×0.93 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 64 % / 63 %, ×1.64 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | -0.3 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.74 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 2 % |
| Error L1 del campo de calor liberado (celdas calientes) | 269 % |
| GA18 / OOD | 0.0 % / 0.8 % |
| Coste | 3.09 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 24.1 K, caliente 1.0 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4965 (464) | 0.0519 | 9 % | 2 % | 11 % |
| llama | 967 (128) | 0.0489 | 9 % | 1 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 100 % | 101 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 100 % | 206 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 63 | 233.0 | +233.0 | 0.6 | 3.5 | 106 % | 9619 % | – | 4059.18 | 1480 / 1752 |
| 2.0 | arranque | 146 | 336.8 | +336.8 | 1.7 | 10.1 | 108 % | 12311 % | – | 264.63 | 1480 / 1886 |
| 2.5 | arranque | 184 | 225.0 | +225.0 | 1.7 | 10.3 | 101 % | 589 % | 2.42 | 2.10 | 1820 / 1932 |
| 3.0 | arranque | 219 | 96.4 | +42.6 | 1.2 | 6.7 | 96 % | 164 % | 1.43 | 1.92 | 2056 / 1961 |
| 3.5 | arranque | 256 | 82.2 | +11.2 | 1.0 | 5.6 | 94 % | 102 % | 1.22 | 2.31 | 2073 / 1971 |
| 4.0 | arranque | 293 | 72.4 | -0.7 | 0.9 | 5.1 | 93 % | 79 % | 1.19 | 2.43 | 2088 / 1980 |
| 4.5 | arranque | 321 | 65.2 | -7.5 | 0.9 | 4.7 | 93 % | 66 % | 1.14 | 2.56 | 2094 / 1991 |
| 5.0 | arranque | 345 | 60.0 | -11.4 | 0.8 | 4.4 | 92 % | 57 % | 1.12 | 2.66 | 2098 / 1999 |
| 7.5 | transicion | 482 | 43.1 | -16.6 | 0.8 | 4.3 | 90 % | 39 % | 1.05 | 2.83 | 2112 / 2020 |
| 10.0 | transicion | 614 | 32.5 | -16.6 | 0.8 | 4.3 | 88 % | 31 % | 1.04 | 3.00 | 2119 / 2036 |
| 12.5 | transicion | 741 | 24.3 | -15.9 | 0.8 | 4.1 | 85 % | 28 % | 1.02 | 3.12 | 2124 / 2049 |
| 15.0 | transicion | 862 | 19.5 | -15.9 | 0.8 | 4.0 | 83 % | 27 % | 1.02 | 3.25 | 2127 / 2059 |
| 17.5 | transicion | 989 | 17.0 | -16.3 | 0.9 | 4.5 | 80 % | 27 % | 1.01 | 3.39 | 2129 / 2068 |
| 20.0 | transicion | 1109 | 16.4 | -16.2 | 1.2 | 5.7 | 77 % | 26 % | 1.00 | 3.52 | 2131 / 2074 |
| 22.5 | transicion | 1241 | 16.1 | -15.6 | 1.5 | 6.7 | 75 % | 24 % | 1.00 | 3.64 | 2133 / 2080 |
| 25.0 | llama | 1369 | 15.6 | -14.5 | 1.9 | 7.3 | 72 % | 22 % | 1.01 | 3.74 | 2134 / 2086 |
