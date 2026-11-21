# Protocolo CFD: C3b_iter2

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2b/iter2/ensemble`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.80 / +0.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +1 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -246 K |
| Media abs dT en la llama | 67.4 K |
| Media abs dT en la boquilla | 1.3 K |
| Media abs dT, celdas calientes | 0.3 K |
| Error L1 de OH, celdas calientes | 56 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **20.8 K** (sesgo -3.4 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 13.9 / 27.6 / 13.4 / 19.5 K |
| p95 abs dT, celdas calientes | 36 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 85 % / 8 %, ×1.75 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 230 % / 6 %, ×3.22 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 12 % / 6 %, ×1.08 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 32 % / 11 %, ×1.21 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | -0.3 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.86 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 6 % / 467 % |
| Error L1 del campo de calor liberado (celdas calientes) | 447 % |
| GA18 / OOD | 0.0 % / 1.7 % |
| Coste | 6.30 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 11.2 K, caliente 5.0 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5004 (478) | 0.034 | 5 % | 1 % | 4 % |
| llama | 1007 (231) | 0.0784 | 10 % | 1 % | 8 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 67 % | 8 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 106 % | 6 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.1 | 61 % | 15 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.1 | 0.2 | 18 % | 44 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 246.5 | -246.5 | 0.6 | 3.5 | 20 % | 84 % | 0.09 | 0.10 | 1820 / 1506 |
| 3.0 | arranque | 161 | 83.5 | -83.5 | 0.6 | 3.4 | 39 % | 37 % | 0.79 | 1.29 | 2056 / 2012 |
| 3.5 | arranque | 210 | 26.7 | -20.7 | 0.4 | 1.7 | 52 % | 13 % | 0.92 | 1.07 | 2073 / 2069 |
| 4.0 | arranque | 252 | 19.0 | -10.1 | 0.3 | 1.3 | 60 % | 7 % | 0.96 | 1.01 | 2088 / 2082 |
| 4.5 | arranque | 288 | 15.4 | -6.2 | 0.3 | 1.1 | 66 % | 5 % | 0.99 | 0.98 | 2094 / 2093 |
| 5.0 | arranque | 316 | 13.3 | -4.5 | 0.3 | 1.1 | 70 % | 4 % | 0.98 | 0.98 | 2098 / 2099 |
| 7.5 | transicion | 463 | 9.9 | -1.6 | 0.5 | 1.3 | 78 % | 5 % | 0.98 | 0.93 | 2112 / 2114 |
| 10.0 | transicion | 599 | 9.6 | -1.2 | 1.0 | 1.5 | 81 % | 8 % | 0.99 | 0.90 | 2119 / 2121 |
| 12.5 | transicion | 736 | 9.4 | -1.6 | 1.7 | 1.9 | 79 % | 12 % | 1.00 | 0.89 | 2124 / 2126 |
| 15.0 | transicion | 862 | 10.0 | -2.1 | 3.3 | 2.6 | 66 % | 25 % | 0.99 | 0.88 | 2127 / 2128 |
| 17.5 | transicion | 991 | 11.9 | -2.6 | 6.9 | 3.8 | 29 % | 73 % | 0.99 | 0.87 | 2129 / 2130 |
| 20.0 | transicion | 1119 | 13.3 | -3.0 | 10.0 | 4.6 | 157 % | 152 % | 0.99 | 0.86 | 2131 / 2131 |
| 22.5 | transicion | 1251 | 14.6 | -3.5 | 11.8 | 5.7 | 130 % | 204 % | 0.99 | 0.86 | 2133 / 2132 |
| 25.0 | llama | 1387 | 20.8 | -3.4 | 13.9 | 9.2 | 85 % | 230 % | 1.00 | 0.86 | 2134 / 2134 |
