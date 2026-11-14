# Protocolo CFD: ood8_s2

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/ood8_s2`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.00 / -1.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +513 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +384 K |
| Media abs dT en la llama | 170.9 K |
| Media abs dT en la boquilla | 5.9 K |
| Media abs dT, celdas calientes | 1.5 K |
| Error L1 de OH, celdas calientes | 1344 % |
| GA18 / OOD | 0.0 % / 0.7 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **8.7 K** (sesgo +0.5 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.8 / 6.6 / 0.4 / 7.6 K |
| p95 abs dT, celdas calientes | 4 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 62 % / 18 %, ×1.47 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 16 % / 5 %, ×0.95 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 4 %, ×0.99 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 23 % / 18 %, ×1.01 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×4.32 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 2070 % |
| Error L1 del campo de calor liberado (celdas calientes) | 2160 % |
| GA18 / OOD | 0.0 % / 6.7 % |
| Coste | 3.06 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 11.3 K, caliente 0.7 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5120 (1656) | 0.092 | 14 % | 25 % | 8 % |
| llama | 990 (307) | 0.0635 | 12 % | 26 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.2 | 0.3 | 1102 % | 101 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 20 | 195.0 | +195.0 | 0.7 | 1.7 | 2175 % | 4424 % | – | 13406.81 | 1480 / 1687 |
| 1.5 | arranque | 107 | 358.5 | +358.5 | 2.0 | 8.1 | 2420 % | 17979 % | – | 8112.73 | 1480 / 1914 |
| 2.0 | arranque | 150 | 384.4 | +384.4 | 2.6 | 12.0 | 1955 % | 15922 % | – | 373.56 | 1480 / 1993 |
| 2.5 | arranque | 183 | 264.3 | +264.3 | 2.5 | 11.5 | 1489 % | 794 % | 2.35 | 3.05 | 1820 / 2019 |
| 3.0 | arranque | 213 | 100.7 | +71.1 | 1.8 | 7.0 | 1187 % | 241 % | 1.38 | 2.67 | 2056 / 2042 |
| 3.5 | arranque | 249 | 75.2 | +35.2 | 1.5 | 5.6 | 979 % | 154 % | 1.20 | 3.18 | 2073 / 2051 |
| 4.0 | arranque | 281 | 62.3 | +22.6 | 1.4 | 4.8 | 822 % | 117 % | 1.15 | 3.37 | 2088 / 2064 |
| 4.5 | arranque | 315 | 52.6 | +16.1 | 1.2 | 4.2 | 703 % | 93 % | 1.11 | 3.51 | 2094 / 2070 |
| 5.0 | arranque | 340 | 45.1 | +12.0 | 1.1 | 3.8 | 608 % | 74 % | 1.09 | 3.61 | 2098 / 2075 |
| 7.5 | transicion | 472 | 20.1 | +3.8 | 0.9 | 2.5 | 349 % | 32 % | 1.03 | 3.75 | 2112 / 2094 |
| 10.0 | transicion | 603 | 11.5 | +0.7 | 0.7 | 1.9 | 231 % | 19 % | 1.02 | 3.93 | 2119 / 2104 |
| 12.5 | transicion | 734 | 9.3 | -0.6 | 0.6 | 1.7 | 153 % | 15 % | 1.01 | 4.06 | 2124 / 2109 |
| 15.0 | transicion | 860 | 10.0 | -0.8 | 0.6 | 1.9 | 95 % | 15 % | 1.01 | 4.17 | 2127 / 2116 |
| 17.5 | transicion | 990 | 9.8 | -0.2 | 0.6 | 2.1 | 69 % | 15 % | 1.00 | 4.25 | 2129 / 2121 |
| 20.0 | transicion | 1109 | 9.5 | +0.2 | 0.6 | 2.4 | 63 % | 15 % | 1.00 | 4.28 | 2131 / 2124 |
| 22.5 | transicion | 1244 | 9.0 | +0.4 | 0.7 | 2.6 | 64 % | 15 % | 1.00 | 4.31 | 2133 / 2127 |
| 25.0 | llama | 1365 | 8.7 | +0.5 | 0.8 | 2.8 | 62 % | 16 % | 1.00 | 4.32 | 2134 / 2130 |
