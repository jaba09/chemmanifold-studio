# Protocolo CFD: C3b_iter1

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2b/iter1/ensemble`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.40 / +0.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +89 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +69 K |
| Media abs dT en la llama | 14.6 K |
| Media abs dT en la boquilla | 0.4 K |
| Media abs dT, celdas calientes | 0.2 K |
| Error L1 de OH, celdas calientes | 78 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **5.5 K** (sesgo -3.1 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.3 / 2.8 / 1.1 / 5.2 K |
| p95 abs dT, celdas calientes | 5 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 70 % / 3 %, ×1.65 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 62 % / 2 %, ×1.58 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 21 % / 1 %, ×1.20 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 5 %, ×1.02 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.88 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 79 % |
| Error L1 del campo de calor liberado (celdas calientes) | 79 % |
| GA18 / OOD | 0.0 % / 0.5 % |
| Coste | 6.12 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 4.4 K, caliente 0.6 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4630 (23) | 0.0102 | 2 % | 1 % | 2 % |
| llama | 907 (48) | 0.0107 | 2 % | 1 % | 2 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 254 % | 5 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 113 % | 11 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.1 | 27 % | 20 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.1 | 0.2 | 19 % | 33 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 80 | 68.9 | +68.9 | 0.3 | 1.4 | 42 % | 33 % | 1.07 | 0.98 | 1820 / 1912 |
| 3.0 | arranque | 165 | 6.2 | +6.0 | 0.2 | 0.6 | 54 % | 8 % | 1.01 | 0.96 | 2056 / 2059 |
| 3.5 | arranque | 214 | 3.5 | +1.1 | 0.2 | 0.4 | 62 % | 5 % | 1.00 | 0.99 | 2073 / 2073 |
| 4.0 | arranque | 253 | 3.2 | -0.1 | 0.2 | 0.4 | 67 % | 4 % | 1.00 | 0.99 | 2088 / 2087 |
| 4.5 | arranque | 288 | 2.8 | -0.8 | 0.2 | 0.4 | 70 % | 4 % | 1.01 | 0.99 | 2094 / 2091 |
| 5.0 | arranque | 315 | 2.8 | -1.1 | 0.2 | 0.5 | 72 % | 4 % | 1.00 | 0.98 | 2098 / 2095 |
| 7.5 | transicion | 459 | 3.5 | -1.1 | 0.3 | 0.7 | 73 % | 3 % | 1.00 | 0.96 | 2112 / 2110 |
| 10.0 | transicion | 598 | 4.5 | -1.3 | 0.3 | 0.9 | 43 % | 3 % | 1.00 | 0.94 | 2119 / 2117 |
| 12.5 | transicion | 733 | 4.6 | -1.7 | 0.5 | 1.1 | 142 % | 8 % | 1.00 | 0.93 | 2124 / 2123 |
| 15.0 | transicion | 858 | 4.4 | -1.7 | 0.6 | 1.3 | 177 % | 9 % | 0.99 | 0.92 | 2127 / 2126 |
| 17.5 | transicion | 989 | 4.2 | -1.7 | 0.7 | 1.3 | 163 % | 11 % | 1.00 | 0.91 | 2129 / 2128 |
| 20.0 | transicion | 1110 | 4.5 | -2.1 | 0.8 | 1.4 | 129 % | 18 % | 1.00 | 0.90 | 2131 / 2131 |
| 22.5 | transicion | 1239 | 4.9 | -2.7 | 0.9 | 1.5 | 92 % | 34 % | 0.99 | 0.89 | 2133 / 2132 |
| 25.0 | llama | 1363 | 5.5 | -3.1 | 1.3 | 1.7 | 70 % | 62 % | 1.00 | 0.88 | 2134 / 2133 |
