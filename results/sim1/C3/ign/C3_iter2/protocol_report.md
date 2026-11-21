# Protocolo CFD: C3_iter2

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2/iter2/ensemble`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.60 / +0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +0 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -122 K |
| Media abs dT en la llama | 31.0 K |
| Media abs dT en la boquilla | 0.6 K |
| Media abs dT, celdas calientes | 0.2 K |
| Error L1 de OH, celdas calientes | 51 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **7.2 K** (sesgo -7.2 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.4 / 3.7 / 1.2 / 10.7 K |
| p95 abs dT, celdas calientes | 5 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 132 % / 7 %, ×2.31 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 13 % / 4 %, ×1.11 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 4 % / 2 %, ×1.02 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 13 %, ×1.18 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.31 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 56 % |
| Error L1 del campo de calor liberado (celdas calientes) | 72 % |
| GA18 / OOD | 0.0 % / 0.2 % |
| Coste | 9.09 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 8.1 K, caliente 0.8 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4450 (118) | 0.0281 | 4 % | 2 % | 8 % |
| llama | 881 (74) | 0.0407 | 6 % | 1 % | 9 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 123 % | 43 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 30 % | 100 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 16 % | 239 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.1 | 0.3 | 35 % | 250 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 121.6 | -121.6 | 0.4 | 1.8 | 44 % | 66 % | 0.66 | 0.63 | 1820 / 1689 |
| 3.0 | arranque | 161 | 22.2 | -19.6 | 0.3 | 1.0 | 47 % | 15 % | 0.97 | 1.25 | 2056 / 2038 |
| 3.5 | arranque | 212 | 12.9 | -8.4 | 0.2 | 0.7 | 50 % | 10 % | 0.98 | 1.18 | 2073 / 2067 |
| 4.0 | arranque | 253 | 10.7 | -6.9 | 0.2 | 0.7 | 53 % | 10 % | 0.99 | 1.16 | 2088 / 2080 |
| 4.5 | arranque | 288 | 9.5 | -6.6 | 0.3 | 0.7 | 55 % | 10 % | 1.00 | 1.16 | 2094 / 2087 |
| 5.0 | arranque | 314 | 8.9 | -6.9 | 0.3 | 0.7 | 57 % | 10 % | 0.99 | 1.18 | 2098 / 2092 |
| 7.5 | transicion | 459 | 8.4 | -6.8 | 0.3 | 0.9 | 54 % | 12 % | 0.99 | 1.19 | 2112 / 2104 |
| 10.0 | transicion | 597 | 8.6 | -7.1 | 0.4 | 1.3 | 112 % | 33 % | 0.99 | 1.21 | 2119 / 2111 |
| 12.5 | transicion | 730 | 8.6 | -7.3 | 0.8 | 1.8 | 356 % | 40 % | 1.00 | 1.23 | 2124 / 2114 |
| 15.0 | transicion | 857 | 8.3 | -7.3 | 1.0 | 1.9 | 291 % | 23 % | 0.99 | 1.24 | 2127 / 2118 |
| 17.5 | transicion | 988 | 8.1 | -7.3 | 1.0 | 1.9 | 198 % | 17 % | 0.99 | 1.26 | 2129 / 2120 |
| 20.0 | transicion | 1109 | 7.7 | -7.3 | 1.1 | 2.0 | 157 % | 14 % | 0.99 | 1.27 | 2131 / 2121 |
| 22.5 | transicion | 1236 | 7.3 | -7.1 | 1.2 | 2.1 | 140 % | 13 % | 0.99 | 1.29 | 2133 / 2123 |
| 25.0 | llama | 1360 | 7.2 | -7.2 | 1.4 | 2.3 | 132 % | 13 % | 1.00 | 1.31 | 2134 / 2124 |
