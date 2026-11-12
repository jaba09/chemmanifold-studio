# Protocolo CFD: tix1_s0

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/tix1_s0`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.20 / -0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +195 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +119 K |
| Media abs dT en la llama | 77.0 K |
| Media abs dT en la boquilla | 2.4 K |
| Media abs dT, celdas calientes | 0.5 K |
| Error L1 de OH, celdas calientes | 95 % |
| GA18 / OOD | 0.0 % / 0.8 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **32.7 K** (sesgo -20.3 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.7 / 14.9 / 0.4 / 31.6 K |
| p95 abs dT, celdas calientes | 5 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 39 % / 20 %, ×1.02 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 100 % / 18 %, ×1.49 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 10 %, ×1.07 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 152 % / 142 %, ×2.52 |
| Volumen por encima de 1500 K, modelo/DI | ×1.03 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×2.09 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 70 % |
| Error L1 del campo de calor liberado (celdas calientes) | 321 % |
| GA18 / OOD | 0.0 % / 64.6 % |
| Coste | 3.16 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 40.2 K, caliente 1.9 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5056 (564) | 0.0578 | 9 % | 5 % | 21 % |
| llama | 967 (119) | 0.035 | 7 % | 2 % | 11 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.2 | 0.4 | 100 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.7 | 99 % | 100 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.2 | 0.7 | 96 % | 100 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.5 | 94 % | 412 % | – | – | 1480 / 1504 |
| 2.5 | arranque | 127 | 121.8 | +119.1 | 0.7 | 4.0 | 95 % | 265 % | 1.59 | 1.90 | 1820 / 1808 |
| 3.0 | arranque | 186 | 74.6 | -37.1 | 0.7 | 3.7 | 92 % | 75 % | 1.18 | 2.19 | 2056 / 1862 |
| 3.5 | arranque | 228 | 73.7 | -50.8 | 0.7 | 3.6 | 92 % | 39 % | 1.08 | 2.54 | 2073 / 1895 |
| 4.0 | arranque | 266 | 66.9 | -48.8 | 0.7 | 3.5 | 92 % | 23 % | 1.07 | 2.71 | 2088 / 1921 |
| 4.5 | arranque | 299 | 64.3 | -49.4 | 0.7 | 3.6 | 92 % | 14 % | 1.06 | 2.74 | 2094 / 1934 |
| 5.0 | arranque | 327 | 60.6 | -47.4 | 0.7 | 3.7 | 96 % | 9 % | 1.05 | 2.85 | 2098 / 1945 |
| 7.5 | transicion | 472 | 50.3 | -40.2 | 1.1 | 5.6 | 108 % | 16 % | 1.03 | 2.76 | 2112 / 1973 |
| 10.0 | transicion | 610 | 44.8 | -34.3 | 1.2 | 6.1 | 93 % | 26 % | 1.02 | 2.73 | 2119 / 1986 |
| 12.5 | transicion | 751 | 41.0 | -29.5 | 1.6 | 6.7 | 87 % | 33 % | 1.02 | 2.61 | 2124 / 1995 |
| 15.0 | transicion | 877 | 38.8 | -27.1 | 3.1 | 7.4 | 117 % | 196 % | 1.02 | 2.50 | 2127 / 2003 |
| 17.5 | transicion | 1009 | 37.2 | -25.2 | 2.6 | 7.9 | 113 % | 181 % | 1.02 | 2.38 | 2129 / 2009 |
| 20.0 | transicion | 1136 | 35.3 | -23.0 | 2.2 | 8.2 | 67 % | 162 % | 1.02 | 2.31 | 2131 / 2014 |
| 22.5 | transicion | 1267 | 33.8 | -21.5 | 1.8 | 8.8 | 39 % | 127 % | 1.02 | 2.20 | 2133 / 2019 |
| 25.0 | llama | 1400 | 32.7 | -20.3 | 1.7 | 9.6 | 39 % | 100 % | 1.03 | 2.09 | 2134 / 2022 |
