# Protocolo CFD: P_mix

Modo: **pure**. Modelo: `/opt/ofb/models/P_mix`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.80 / -0.60 ms |
| Máximo exceso de Tmax del dominio sobre DI | +382 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +297 K |
| Media abs dT en la llama | 109.7 K |
| Media abs dT en la boquilla | 3.2 K |
| Media abs dT, celdas calientes | 0.6 K |
| Error L1 de OH, celdas calientes | 31 % |
| GA18 / OOD | 0.0 % / 0.1 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **7.3 K** (sesgo -3.5 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.5 / 3.4 / 0.3 / 4.6 K |
| p95 abs dT, celdas calientes | 2 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 60 % / 18 %, ×1.60 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 6 % / 3 %, ×1.05 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 6 %, ×0.98 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 16 %, ×1.06 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×4.48 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 31 % |
| Error L1 del campo de calor liberado (celdas calientes) | 341 % |
| GA18 / OOD | 0.0 % / 0.0 % |
| Coste | 14.19 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 13.3 K, caliente 0.5 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4319 (0) | 0.0156 | 2 % | 2 % | 5 % |
| llama | 808 (0) | 0.0107 | 2 % | 2 % | 6 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 87 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 59 % | 100 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 37 % | 425 % | – | – | 1480 / 1488 |
| 2.0 | arranque | 102 | 296.5 | +296.5 | 1.0 | 6.1 | 29 % | 6636 % | – | 610.53 | 1480 / 1817 |
| 2.5 | arranque | 163 | 227.0 | +227.0 | 1.4 | 8.4 | 18 % | 422 % | 2.09 | 2.67 | 1820 / 1953 |
| 3.0 | arranque | 203 | 68.7 | +36.6 | 0.8 | 4.7 | 13 % | 110 % | 1.30 | 2.48 | 2056 / 1990 |
| 3.5 | arranque | 237 | 53.8 | +7.9 | 0.7 | 3.8 | 13 % | 64 % | 1.15 | 2.99 | 2073 / 2009 |
| 4.0 | arranque | 272 | 46.0 | -0.1 | 0.6 | 3.3 | 16 % | 46 % | 1.10 | 3.20 | 2088 / 2025 |
| 4.5 | arranque | 307 | 40.0 | -3.6 | 0.6 | 3.0 | 19 % | 37 % | 1.10 | 3.35 | 2094 / 2033 |
| 5.0 | arranque | 331 | 36.0 | -6.2 | 0.6 | 2.7 | 22 % | 31 % | 1.07 | 3.52 | 2098 / 2041 |
| 7.5 | transicion | 472 | 23.3 | -7.7 | 0.5 | 2.2 | 24 % | 17 % | 1.02 | 3.75 | 2112 / 2064 |
| 10.0 | transicion | 605 | 17.6 | -7.5 | 0.5 | 2.1 | 15 % | 13 % | 1.02 | 4.00 | 2119 / 2076 |
| 12.5 | transicion | 738 | 14.0 | -6.5 | 0.5 | 2.0 | 58 % | 11 % | 1.01 | 4.11 | 2124 / 2085 |
| 15.0 | transicion | 861 | 11.6 | -5.6 | 0.5 | 2.1 | 97 % | 11 % | 1.01 | 4.21 | 2127 / 2092 |
| 17.5 | transicion | 991 | 10.0 | -5.1 | 0.5 | 2.1 | 98 % | 9 % | 1.01 | 4.31 | 2129 / 2098 |
| 20.0 | transicion | 1109 | 8.8 | -4.5 | 0.6 | 2.1 | 84 % | 8 % | 1.00 | 4.37 | 2131 / 2104 |
| 22.5 | transicion | 1240 | 7.9 | -4.0 | 0.5 | 2.1 | 71 % | 7 % | 1.00 | 4.44 | 2133 / 2109 |
| 25.0 | llama | 1364 | 7.3 | -3.5 | 0.5 | 2.1 | 60 % | 6 % | 1.00 | 4.48 | 2134 / 2113 |
