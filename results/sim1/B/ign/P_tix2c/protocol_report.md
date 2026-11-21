# Protocolo CFD: P_tix2c

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2c`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.80 / -0.60 ms |
| Máximo exceso de Tmax del dominio sobre DI | +492 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +377 K |
| Media abs dT en la llama | 345.3 K |
| Media abs dT en la boquilla | 21.0 K |
| Media abs dT, celdas calientes | 3.4 K |
| Error L1 de OH, celdas calientes | 73 % |
| GA18 / OOD | 0.0 % / 0.5 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **457.7 K** (sesgo +363.6 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 130.5 / 302.5 / 26.3 / 325.0 K |
| p95 abs dT, celdas calientes | 671 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 290 % / 1054 %, ×2.75 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 384 % / 388 %, ×3.35 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 95 % / 101 %, ×0.14 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 1739 % / 1664 %, ×16.81 |
| Volumen por encima de 1500 K, modelo/DI | ×10.13 |
| Punta / base de la llama en el eje, modelo - DI | +32.4 / +9.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×862.21 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 257117 % |
| Error L1 del campo de calor liberado (celdas calientes) | 311468 % |
| GA18 / OOD | 0.0 % / 5.5 % |
| Coste | 7.20 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 459.6 K, caliente 85.1 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5588 (2219) | 0.432 | 14 % | 18 % | 12 % |
| llama | 1087 (332) | 0.0886 | 9 % | 11 % | 4 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 60 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 35 % | 101 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 36 % | 279 % | – | – | 1480 / 1486 |
| 2.0 | arranque | 101 | 377.1 | +377.1 | 1.3 | 7.9 | 51 % | 4522 % | – | 129.67 | 1480 / 1972 |
| 2.5 | arranque | 162 | 278.7 | +253.9 | 1.9 | 11.1 | 64 % | 647 % | 1.91 | 0.67 | 1820 / 2031 |
| 3.0 | arranque | 238 | 372.1 | -111.2 | 2.9 | 17.5 | 76 % | 228 % | 1.16 | 2064.41 | 2056 / 2035 |
| 3.5 | arranque | 328 | 346.1 | -81.9 | 4.0 | 24.5 | 84 % | 276 % | 1.12 | 164.70 | 2073 / 2050 |
| 4.0 | arranque | 472 | 344.0 | +39.2 | 6.0 | 37.7 | 99 % | 309 % | 1.38 | 286.24 | 2088 / 2069 |
| 4.5 | arranque | 678 | 353.2 | +161.2 | 8.3 | 52.1 | 107 % | 371 % | 1.72 | 147.94 | 2094 / 2106 |
| 5.0 | arranque | 903 | 346.2 | +224.9 | 9.3 | 58.7 | 116 % | 402 % | 2.05 | 18.87 | 2098 / 2119 |
| 7.5 | transicion | 1693 | 384.4 | +269.4 | 24.8 | 156.4 | 164 % | 770 % | 3.39 | 117.87 | 2112 / 2116 |
| 10.0 | transicion | 4617 | 439.6 | +388.7 | 48.6 | 230.8 | 194 % | 1035 % | 6.82 | 16.47 | 2119 / 2152 |
| 12.5 | transicion | 5979 | 461.0 | +365.8 | 73.2 | 266.7 | 199 % | 815 % | 8.68 | 820.39 | 2124 / 2177 |
| 15.0 | transicion | 7612 | 443.3 | +400.2 | 83.4 | 281.9 | 231 % | 1008 % | 9.49 | 48.92 | 2127 / 2171 |
| 17.5 | transicion | 8794 | 493.2 | +405.2 | 107.9 | 368.9 | 258 % | 828 % | 9.70 | 978.09 | 2129 / 2204 |
| 20.0 | transicion | 9910 | 513.6 | +463.2 | 127.3 | 414.2 | 310 % | 735 % | 10.24 | 91.98 | 2131 / 2199 |
| 22.5 | transicion | 10637 | 482.0 | +421.3 | 130.7 | 366.3 | 303 % | 545 % | 10.74 | 318.31 | 2133 / 2218 |
| 25.0 | llama | 10437 | 457.7 | +363.6 | 130.5 | 332.0 | 290 % | 384 % | 10.13 | 862.21 | 2134 / 2216 |
