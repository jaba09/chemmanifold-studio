# Protocolo CFD: isann_arc22

Modo: **di**. Modelo: `GA18 (DI)`. Estado: running (hasta 150.0 ms). Puntuación **no válida** (no llega a 150 ms).

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | – / 100.20 / – ms |
| Máximo exceso de Tmax del dominio sobre DI | – K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +0 K |
| Media abs dT en la llama | 0.0 K |
| Media abs dT en la boquilla | 0.0 K |
| Media abs dT, celdas calientes | 0.0 K |
| Error L1 de OH, celdas calientes | 0 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **7.3 K** (sesgo +0.3 K) |
| Deriva de ese error (100-150 ms) | +1.68 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 11.6 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 14.6 / 20.0 / 13.0 / 23.2 K |
| p95 abs dT, celdas calientes | 53 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 4 %, ×0.99 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 13 % / 8 %, ×1.06 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 6 % / 10 %, ×0.96 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 7 %, ×1.00 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.01 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 7 % |
| Error L1 del campo de calor liberado (celdas calientes) | 22 % |
| GA18 / OOD | – / – |
| Coste | 5.87 s por paso (None procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 95133 (0) | 0.0728 | 10 % | 5 % | 4 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4349 | 0.1 | -0.0 | 0.1 | 0.2 | 0 % | 0 % | 1.00 | 1.00 | 2114 / 2114 |
| 105.0 | llama | 4274 | 0.1 | +0.0 | 0.1 | 0.2 | 0 % | 0 % | 1.00 | 1.00 | 2114 / 2114 |
| 107.5 | llama | 4225 | 13.1 | -11.0 | 10.1 | 11.6 | 9 % | 13 % | 0.97 | 0.97 | 2114 / 2113 |
| 110.0 | llama | 4193 | 13.3 | -10.1 | 13.3 | 12.7 | 13 % | 12 % | 0.97 | 0.93 | 2113 / 2111 |
| 112.5 | llama | 4182 | 5.8 | -2.7 | 8.5 | 6.2 | 8 % | 9 % | 0.98 | 0.95 | 2113 / 2113 |
| 115.0 | llama | 4201 | 3.5 | +0.2 | 6.1 | 5.2 | 7 % | 8 % | 0.99 | 0.95 | 2113 / 2114 |
| 117.5 | llama | 4185 | 3.4 | +1.0 | 7.3 | 7.9 | 7 % | 8 % | 0.99 | 0.94 | 2112 / 2114 |
| 120.0 | llama | 4182 | 4.2 | +1.0 | 9.2 | 9.1 | 7 % | 8 % | 0.99 | 0.93 | 2112 / 2113 |
| 122.5 | llama | 4177 | 4.4 | +1.5 | 10.4 | 8.8 | 5 % | 7 % | 0.99 | 1.02 | 2112 / 2113 |
| 125.0 | llama | 4192 | 4.7 | +2.7 | 11.4 | 8.5 | 5 % | 7 % | 1.00 | 1.03 | 2111 / 2113 |
| 127.5 | llama | 4202 | 5.6 | +3.7 | 13.0 | 9.4 | 5 % | 8 % | 1.00 | 1.04 | 2111 / 2113 |
| 130.0 | llama | 4199 | 6.3 | +4.3 | 14.8 | 11.2 | 5 % | 9 % | 1.00 | 1.04 | 2110 / 2112 |
| 132.5 | llama | 4199 | 7.1 | +4.4 | 16.5 | 14.1 | 6 % | 11 % | 1.00 | 0.99 | 2109 / 2112 |
| 135.0 | llama | 4222 | 8.0 | +4.0 | 18.0 | 17.6 | 6 % | 12 % | 1.01 | 0.95 | 2109 / 2112 |
| 137.5 | llama | 4203 | 8.6 | +2.6 | 19.1 | 21.6 | 7 % | 14 % | 1.00 | 0.98 | 2108 / 2112 |
| 140.0 | llama | 4165 | 8.9 | +1.3 | 19.3 | 24.3 | 7 % | 17 % | 0.99 | 1.00 | 2108 / 2111 |
| 142.5 | llama | 4166 | 9.9 | +0.5 | 21.8 | 29.2 | 8 % | 24 % | 0.99 | 1.04 | 2108 / 2111 |
| 145.0 | llama | 4152 | 12.0 | +0.2 | 26.4 | 35.5 | 8 % | 31 % | 0.98 | 1.04 | 2107 / 2112 |
| 147.5 | llama | 4144 | 13.8 | +0.2 | 32.4 | 37.2 | 9 % | 37 % | 0.97 | 1.17 | 2107 / 2115 |
| 150.0 | llama | 4140 | 13.4 | +1.3 | 33.9 | 31.4 | 8 % | 35 % | 0.97 | 1.14 | 2106 / 2119 |
