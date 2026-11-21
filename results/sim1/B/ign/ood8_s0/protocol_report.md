# Protocolo CFD: ood8_s0

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/ood8_s0`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.40 / -1.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +469 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +370 K |
| Media abs dT en la llama | 146.9 K |
| Media abs dT en la boquilla | 4.4 K |
| Media abs dT, celdas calientes | 0.8 K |
| Error L1 de OH, celdas calientes | 62 % |
| GA18 / OOD | 0.0 % / 1.6 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **65.1 K** (sesgo -6.1 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 7.3 / 60.2 / 3.7 / 184.0 K |
| p95 abs dT, celdas calientes | 21 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 473 % / 44 %, ×5.64 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 453 % / 30 %, ×5.23 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 39 % / 56 %, ×0.63 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 1315 % / 71 %, ×13.39 |
| Volumen por encima de 1500 K, modelo/DI | ×0.90 |
| Punta / base de la llama en el eje, modelo - DI | -0.5 / -0.2 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.90 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / -39212 % |
| Error L1 del campo de calor liberado (celdas calientes) | 36115 % |
| GA18 / OOD | 0.0 % / 74.9 % |
| Coste | 3.24 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 27.7 K, caliente 3.2 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5309 (3066) | 0.369 | 38 % | 35 % | 28 % |
| llama | 950 (607) | 0.481 | 50 % | 45 % | 29 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 96 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.3 | 90 % | 108 % | – | – | 1480 / 1481 |
| 1.5 | arranque | 61 | 261.1 | +261.1 | 0.6 | 3.4 | 89 % | 6945 % | – | 7363.86 | 1480 / 1774 |
| 2.0 | arranque | 136 | 370.5 | +370.5 | 1.6 | 9.7 | 79 % | 9086 % | – | 231.05 | 1480 / 1950 |
| 2.5 | arranque | 178 | 254.3 | +254.3 | 1.6 | 9.9 | 17 % | 439 % | 2.22 | 1.93 | 1820 / 1992 |
| 3.0 | arranque | 210 | 86.0 | +59.8 | 1.0 | 5.7 | 25 % | 111 % | 1.33 | 1.71 | 2056 / 2018 |
| 3.5 | arranque | 244 | 62.9 | +27.5 | 0.8 | 4.4 | 36 % | 64 % | 1.18 | 2.01 | 2073 / 2030 |
| 4.0 | arranque | 275 | 53.0 | +14.5 | 0.7 | 3.9 | 61 % | 49 % | 1.13 | 2.13 | 2088 / 2039 |
| 4.5 | arranque | 308 | 45.8 | +8.1 | 0.7 | 3.5 | 66 % | 41 % | 1.09 | 2.20 | 2094 / 2050 |
| 5.0 | arranque | 335 | 41.1 | +4.5 | 0.6 | 3.3 | 66 % | 37 % | 1.07 | 2.28 | 2098 / 2056 |
| 7.5 | transicion | 472 | 24.6 | -1.0 | 1.1 | 2.8 | 389 % | 228 % | 1.00 | 2.19 | 2112 / 2078 |
| 10.0 | transicion | 598 | 15.5 | -3.3 | 1.4 | 2.5 | 338 % | 396 % | 0.99 | 2.19 | 2119 / 2091 |
| 12.5 | transicion | 732 | 7.9 | -3.5 | 2.0 | 3.3 | 381 % | 474 % | 0.97 | 2.12 | 2124 / 2100 |
| 15.0 | transicion | 868 | 15.2 | -3.4 | 2.8 | 6.7 | 409 % | 509 % | 0.95 | 2.06 | 2127 / 2107 |
| 17.5 | transicion | 1014 | 28.9 | -3.0 | 3.9 | 11.7 | 436 % | 517 % | 0.94 | 2.02 | 2129 / 2114 |
| 20.0 | transicion | 1153 | 44.3 | -2.3 | 5.1 | 17.6 | 450 % | 501 % | 0.93 | 1.96 | 2131 / 2121 |
| 22.5 | transicion | 1290 | 57.3 | -2.7 | 6.3 | 22.8 | 465 % | 478 % | 0.92 | 1.93 | 2133 / 2131 |
| 25.0 | llama | 1423 | 65.1 | -6.1 | 7.3 | 27.6 | 473 % | 453 % | 0.90 | 1.90 | 2134 / 2138 |
