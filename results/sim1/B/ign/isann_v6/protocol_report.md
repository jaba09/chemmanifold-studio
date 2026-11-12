# Protocolo CFD: isann_v6

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/isann_v6`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.20 / -0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +281 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +197 K |
| Media abs dT en la llama | 41.3 K |
| Media abs dT en la boquilla | 1.0 K |
| Media abs dT, celdas calientes | 0.3 K |
| Error L1 de OH, celdas calientes | 48 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **5.9 K** (sesgo +2.0 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.6 / 5.5 / 0.4 / 6.1 K |
| p95 abs dT, celdas calientes | 3 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 50 % / 7 %, ×0.62 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 10 % / 6 %, ×0.91 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 3 %, ×1.01 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 17 %, ×0.91 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | -0.3 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.91 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 9 % |
| Error L1 del campo de calor liberado (celdas calientes) | 37 % |
| GA18 / OOD | 0.0 % / 0.0 % |
| Coste | 3.04 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 7.7 K, caliente 0.5 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4348 (0) | 0.0259 | 4 % | 1 % | 9 % |
| llama | 815 (0) | 0.0166 | 3 % | 1 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 107 % | 22 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.2 | 113 % | 9 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 76 % | 7 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.6 | 57 % | 587 % | – | – | 1480 / 1547 |
| 2.5 | arranque | 115 | 197.2 | +197.2 | 0.8 | 4.7 | 45 % | 136 % | 1.47 | 1.55 | 1820 / 2008 |
| 3.0 | arranque | 175 | 28.3 | +28.3 | 0.4 | 1.7 | 32 % | 26 % | 1.08 | 0.98 | 2056 / 2067 |
| 3.5 | arranque | 217 | 7.8 | +7.7 | 0.2 | 0.8 | 23 % | 9 % | 1.01 | 1.07 | 2073 / 2082 |
| 4.0 | arranque | 253 | 3.8 | +2.6 | 0.2 | 0.5 | 15 % | 5 % | 1.00 | 1.10 | 2088 / 2094 |
| 4.5 | arranque | 288 | 4.6 | +0.2 | 0.2 | 0.5 | 8 % | 4 % | 1.00 | 1.11 | 2094 / 2098 |
| 5.0 | arranque | 315 | 6.2 | -0.7 | 0.2 | 0.7 | 5 % | 4 % | 0.99 | 1.10 | 2098 / 2101 |
| 7.5 | transicion | 461 | 9.0 | -1.3 | 0.3 | 1.3 | 26 % | 7 % | 0.98 | 1.15 | 2112 / 2114 |
| 10.0 | transicion | 599 | 9.1 | -0.5 | 0.4 | 1.6 | 36 % | 9 % | 0.99 | 1.11 | 2119 / 2120 |
| 12.5 | transicion | 737 | 8.3 | -0.0 | 0.4 | 1.8 | 41 % | 9 % | 0.98 | 1.09 | 2124 / 2125 |
| 15.0 | transicion | 862 | 7.7 | +0.5 | 0.5 | 1.9 | 45 % | 10 % | 0.98 | 1.07 | 2127 / 2128 |
| 17.5 | transicion | 990 | 7.2 | +0.9 | 0.5 | 2.0 | 47 % | 10 % | 0.99 | 1.02 | 2129 / 2131 |
| 20.0 | transicion | 1113 | 6.6 | +1.3 | 0.6 | 2.1 | 48 % | 10 % | 0.99 | 1.00 | 2131 / 2133 |
| 22.5 | transicion | 1244 | 6.3 | +1.7 | 0.6 | 2.2 | 49 % | 10 % | 0.99 | 0.95 | 2133 / 2135 |
| 25.0 | llama | 1370 | 5.9 | +2.0 | 0.6 | 2.4 | 50 % | 10 % | 0.99 | 0.91 | 2134 / 2137 |
