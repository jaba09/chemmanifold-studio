# Protocolo CFD: ood8_s1

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/ood8_s1`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.40 / -1.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +454 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +356 K |
| Media abs dT en la llama | 138.2 K |
| Media abs dT en la boquilla | 4.8 K |
| Media abs dT, celdas calientes | 1.2 K |
| Error L1 de OH, celdas calientes | 810 % |
| GA18 / OOD | 0.0 % / 7.4 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **62.6 K** (sesgo -42.4 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 4.2 / 54.1 / 0.5 / 209.4 K |
| p95 abs dT, celdas calientes | 18 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 90 % / 57 %, ×1.13 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 42 % / 38 %, ×0.63 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 27 % / 53 %, ×0.74 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 270 % / 213 %, ×3.11 |
| Volumen por encima de 1500 K, modelo/DI | ×0.89 |
| Punta / base de la llama en el eje, modelo - DI | -0.5 / +0.3 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×-21.59 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / -10643 % |
| Error L1 del campo de calor liberado (celdas calientes) | 15289 % |
| GA18 / OOD | 0.0 % / 30.5 % |
| Coste | 3.21 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 51.4 K, caliente 2.3 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5307 (3316) | 0.184 | 20 % | 34 % | 14 % |
| llama | 985 (617) | 0.174 | 26 % | 36 % | 30 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.2 | 0.4 | 68 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.6 | 40 % | 295 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 67 | 256.8 | +256.8 | 0.8 | 3.7 | 444 % | 8433 % | – | 5284.61 | 1480 / 1766 |
| 2.0 | arranque | 140 | 355.6 | +355.6 | 2.2 | 10.4 | 1790 % | 10668 % | – | 223.49 | 1480 / 1934 |
| 2.5 | arranque | 174 | 235.7 | +235.7 | 2.6 | 10.6 | 1932 % | 695 % | 2.24 | 1.69 | 1820 / 1963 |
| 3.0 | arranque | 209 | 80.7 | +42.3 | 1.8 | 6.4 | 1351 % | 238 % | 1.35 | 1.49 | 2056 / 1985 |
| 3.5 | arranque | 245 | 61.8 | +9.0 | 1.5 | 5.0 | 951 % | 153 % | 1.19 | 1.75 | 2073 / 1998 |
| 4.0 | arranque | 274 | 48.4 | -1.5 | 1.2 | 4.1 | 674 % | 108 % | 1.13 | 1.87 | 2088 / 2013 |
| 4.5 | arranque | 305 | 36.7 | -8.9 | 1.0 | 3.3 | 488 % | 77 % | 1.09 | 0.73 | 2094 / 2021 |
| 5.0 | arranque | 327 | 30.0 | -14.5 | 0.9 | 3.1 | 358 % | 54 % | 1.07 | -0.28 | 2098 / 2030 |
| 7.5 | transicion | 461 | 26.5 | -23.2 | 0.7 | 3.7 | 61 % | 25 % | 0.99 | -2.54 | 2112 / 2059 |
| 10.0 | transicion | 597 | 40.9 | -29.7 | 1.2 | 6.7 | 98 % | 30 % | 0.96 | -5.42 | 2119 / 2073 |
| 12.5 | transicion | 733 | 50.3 | -34.9 | 1.7 | 9.9 | 77 % | 33 % | 0.93 | -7.55 | 2124 / 2080 |
| 15.0 | transicion | 858 | 57.0 | -38.3 | 2.4 | 13.4 | 163 % | 40 % | 0.91 | -8.62 | 2127 / 2087 |
| 17.5 | transicion | 991 | 59.6 | -40.5 | 2.8 | 16.3 | 103 % | 42 % | 0.90 | -12.69 | 2129 / 2093 |
| 20.0 | transicion | 1116 | 62.3 | -41.5 | 3.3 | 19.6 | 97 % | 41 % | 0.89 | -14.70 | 2131 / 2099 |
| 22.5 | transicion | 1244 | 62.9 | -42.3 | 3.7 | 22.5 | 83 % | 41 % | 0.89 | -18.53 | 2133 / 2104 |
| 25.0 | llama | 1371 | 62.6 | -42.4 | 4.2 | 25.6 | 90 % | 42 % | 0.89 | -21.59 | 2134 / 2107 |
