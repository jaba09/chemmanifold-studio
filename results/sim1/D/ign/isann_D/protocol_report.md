# Protocolo CFD: isann_D

Modo: **pure**. Modelo: `/opt/ofb/models/isann_D`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.20 / -0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +280 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +190 K |
| Media abs dT en la llama | 41.4 K |
| Media abs dT en la boquilla | 1.1 K |
| Media abs dT, celdas calientes | 0.3 K |
| Error L1 de OH, celdas calientes | 29 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **4.1 K** (sesgo +0.8 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.5 / 3.3 / 0.3 / 5.2 K |
| p95 abs dT, celdas calientes | 2 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 49 % / 2 %, ×0.54 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 6 %, ×0.95 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 2 %, ×1.00 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 6 % / 5 %, ×0.95 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.01 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 24 % |
| Error L1 del campo de calor liberado (celdas calientes) | 31 % |
| GA18 / OOD | 0.0 % / 0.0 % |
| Coste | 2.97 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 4.4 K, caliente 0.4 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4391 (46) | 0.0158 | 2 % | 1 % | 3 % |
| llama | 822 (5) | 0.0119 | 2 % | 0 % | 4 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 71 % | 23 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 67 % | 19 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.1 | 47 % | 14 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.5 | 31 % | 361 % | – | – | 1480 / 1517 |
| 2.5 | arranque | 118 | 190.5 | +190.5 | 0.8 | 4.5 | 21 % | 121 % | 1.47 | 1.05 | 1820 / 2012 |
| 3.0 | arranque | 183 | 30.2 | +30.0 | 0.4 | 1.9 | 11 % | 23 % | 1.11 | 0.86 | 2056 / 2065 |
| 3.5 | arranque | 221 | 12.2 | +11.2 | 0.3 | 1.2 | 6 % | 9 % | 1.05 | 0.96 | 2073 / 2078 |
| 4.0 | arranque | 255 | 7.4 | +6.5 | 0.2 | 0.9 | 7 % | 5 % | 1.02 | 0.99 | 2088 / 2091 |
| 4.5 | arranque | 288 | 4.8 | +4.3 | 0.2 | 0.7 | 12 % | 3 % | 1.03 | 1.00 | 2094 / 2097 |
| 5.0 | arranque | 318 | 3.6 | +3.2 | 0.2 | 0.6 | 16 % | 3 % | 1.00 | 1.02 | 2098 / 2101 |
| 7.5 | transicion | 460 | 2.2 | +2.0 | 0.3 | 0.5 | 30 % | 3 % | 1.00 | 1.00 | 2112 / 2115 |
| 10.0 | transicion | 598 | 3.8 | +1.9 | 0.3 | 0.8 | 37 % | 4 % | 1.00 | 1.01 | 2119 / 2123 |
| 12.5 | transicion | 735 | 4.9 | +1.6 | 0.4 | 1.0 | 43 % | 5 % | 1.00 | 1.00 | 2124 / 2129 |
| 15.0 | transicion | 861 | 5.3 | +1.1 | 0.4 | 1.2 | 52 % | 5 % | 1.00 | 0.99 | 2127 / 2131 |
| 17.5 | transicion | 990 | 5.2 | +0.9 | 0.4 | 1.3 | 48 % | 6 % | 1.00 | 1.00 | 2129 / 2133 |
| 20.0 | transicion | 1111 | 4.9 | +0.8 | 0.4 | 1.4 | 48 % | 6 % | 1.00 | 1.00 | 2131 / 2135 |
| 22.5 | transicion | 1242 | 4.5 | +0.9 | 0.5 | 1.5 | 49 % | 7 % | 1.00 | 1.01 | 2133 / 2137 |
| 25.0 | llama | 1366 | 4.1 | +0.8 | 0.5 | 1.5 | 49 % | 7 % | 1.00 | 1.01 | 2134 / 2138 |
