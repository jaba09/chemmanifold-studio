# Protocolo CFD: isat1e-3

Modo: **di**. Modelo: `GA18 (DI)`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.40 / -1.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +567 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +401 K |
| Media abs dT en la llama | 151.7 K |
| Media abs dT en la boquilla | 4.6 K |
| Media abs dT, celdas calientes | 1.0 K |
| Error L1 de OH, celdas calientes | 120 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **12.0 K** (sesgo +8.1 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.4 / 8.1 / 1.0 / 5.4 K |
| p95 abs dT, celdas calientes | 6 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 13 % / 7 %, ×1.09 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 3 %, ×1.03 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 5 %, ×1.01 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 9 %, ×1.01 |
| Volumen por encima de 1500 K, modelo/DI | ×1.07 |
| Punta / base de la llama en el eje, modelo - DI | +0.3 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.98 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 9 % |
| Error L1 del campo de calor liberado (celdas calientes) | 30 % |
| GA18 / OOD | – / – |
| Coste | 1.87 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 13.1 K, caliente 1.2 K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 74 % | 219 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.3 | 0.4 | 134 % | 13162 % | – | – | 1480 / 1481 |
| 1.5 | arranque | 63 | 289.8 | +289.8 | 0.8 | 4.0 | 177 % | 20376 % | – | 4447.12 | 1480 / 1873 |
| 2.0 | arranque | 137 | 401.4 | +401.4 | 1.8 | 10.4 | 155 % | 14789 % | – | 136.58 | 1480 / 2047 |
| 2.5 | arranque | 176 | 280.0 | +280.0 | 1.9 | 10.5 | 133 % | 631 % | 2.24 | 0.90 | 1820 / 2072 |
| 3.0 | arranque | 210 | 83.8 | +75.9 | 1.4 | 5.9 | 124 % | 165 % | 1.35 | 0.77 | 2056 / 2084 |
| 3.5 | arranque | 241 | 53.1 | +39.9 | 1.2 | 4.3 | 120 % | 94 % | 1.20 | 0.90 | 2073 / 2092 |
| 4.0 | arranque | 277 | 41.4 | +27.1 | 1.0 | 3.5 | 115 % | 67 % | 1.15 | 0.93 | 2088 / 2096 |
| 4.5 | arranque | 308 | 34.2 | +20.3 | 0.9 | 3.3 | 92 % | 48 % | 1.11 | 0.97 | 2094 / 2100 |
| 5.0 | arranque | 336 | 29.9 | +16.9 | 0.8 | 3.3 | 78 % | 37 % | 1.11 | 0.99 | 2098 / 2107 |
| 7.5 | transicion | 475 | 18.4 | +9.5 | 0.9 | 3.8 | 71 % | 19 % | 1.06 | 0.97 | 2112 / 2116 |
| 10.0 | transicion | 613 | 13.7 | +6.8 | 1.2 | 4.0 | 45 % | 9 % | 1.05 | 0.98 | 2119 / 2124 |
| 12.5 | transicion | 749 | 12.3 | +6.3 | 1.1 | 4.4 | 33 % | 6 % | 1.05 | 1.03 | 2124 / 2128 |
| 15.0 | transicion | 873 | 12.3 | +6.3 | 1.2 | 4.7 | 24 % | 5 % | 1.04 | 0.98 | 2127 / 2129 |
| 17.5 | transicion | 1013 | 12.0 | +6.4 | 1.3 | 4.9 | 19 % | 4 % | 1.05 | 0.98 | 2129 / 2132 |
| 20.0 | transicion | 1137 | 11.1 | +6.2 | 1.3 | 5.2 | 21 % | 4 % | 1.06 | 0.96 | 2131 / 2134 |
| 22.5 | transicion | 1276 | 11.8 | +6.9 | 1.5 | 5.9 | 16 % | 4 % | 1.08 | 1.00 | 2133 / 2138 |
| 25.0 | llama | 1408 | 12.0 | +8.1 | 1.4 | 6.2 | 13 % | 3 % | 1.07 | 0.98 | 2134 / 2140 |
