# Protocolo CFD: P_tix2h

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2h`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.60 / +0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +3 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -212 K |
| Media abs dT en la llama | 71.9 K |
| Media abs dT en la boquilla | 1.4 K |
| Media abs dT, celdas calientes | 0.4 K |
| Error L1 de OH, celdas calientes | 69 % |
| GA18 / OOD | 0.0 % / 0.2 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **8.2 K** (sesgo -8.0 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.9 / 4.3 / 0.5 / 7.1 K |
| p95 abs dT, celdas calientes | 3 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 119 % / 22 %, ×1.32 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 17 % / 7 %, ×1.16 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 8 %, ×0.97 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 25 % / 18 %, ×1.07 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×5.53 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 47 % |
| Error L1 del campo de calor liberado (celdas calientes) | 453 % |
| GA18 / OOD | 0.0 % / 0.0 % |
| Coste | 6.51 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 12.6 K, caliente 0.6 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4320 (20) | 0.0253 | 5 % | 2 % | 7 % |
| llama | 809 (1) | 0.0174 | 3 % | 2 % | 5 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 100 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.2 | 99 % | 100 % | – | – | 1480 / 1481 |
| 1.5 | arranque | 0 | – | – | 0.2 | 0.3 | 97 % | 99 % | – | – | 1480 / 1482 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.4 | 93 % | 91 % | – | – | 1480 / 1483 |
| 2.5 | arranque | 63 | 211.8 | -211.8 | 0.6 | 2.9 | 85 % | 73 % | 0.33 | 0.23 | 1820 / 1557 |
| 3.0 | arranque | 161 | 80.8 | -80.8 | 0.5 | 2.4 | 71 % | 45 % | 0.95 | 3.68 | 2056 / 1888 |
| 3.5 | arranque | 218 | 41.9 | -36.1 | 0.4 | 1.8 | 57 % | 45 % | 1.00 | 3.42 | 2073 / 1981 |
| 4.0 | arranque | 255 | 36.3 | -29.4 | 0.5 | 2.0 | 40 % | 37 % | 1.02 | 3.76 | 2088 / 2004 |
| 4.5 | arranque | 290 | 32.1 | -25.9 | 0.5 | 1.9 | 27 % | 32 % | 1.03 | 3.94 | 2094 / 2023 |
| 5.0 | arranque | 321 | 28.8 | -23.2 | 0.4 | 1.9 | 18 % | 27 % | 1.01 | 4.15 | 2098 / 2032 |
| 7.5 | transicion | 462 | 19.3 | -17.7 | 0.5 | 1.7 | 32 % | 16 % | 1.00 | 4.53 | 2112 / 2057 |
| 10.0 | transicion | 596 | 15.8 | -15.5 | 0.5 | 1.8 | 51 % | 12 % | 0.99 | 4.92 | 2119 / 2069 |
| 12.5 | transicion | 730 | 13.0 | -13.0 | 0.6 | 1.9 | 73 % | 11 % | 1.00 | 5.10 | 2124 / 2077 |
| 15.0 | transicion | 856 | 11.3 | -11.3 | 0.6 | 2.0 | 135 % | 15 % | 0.99 | 5.24 | 2127 / 2085 |
| 17.5 | transicion | 986 | 10.4 | -10.4 | 0.7 | 2.1 | 136 % | 17 % | 0.99 | 5.36 | 2129 / 2091 |
| 20.0 | transicion | 1108 | 9.4 | -9.4 | 0.7 | 2.2 | 130 % | 17 % | 0.99 | 5.43 | 2131 / 2097 |
| 22.5 | transicion | 1236 | 8.7 | -8.7 | 0.8 | 2.3 | 124 % | 17 % | 0.99 | 5.49 | 2133 / 2103 |
| 25.0 | llama | 1359 | 8.2 | -8.0 | 0.9 | 2.5 | 119 % | 17 % | 1.00 | 5.53 | 2134 / 2107 |
