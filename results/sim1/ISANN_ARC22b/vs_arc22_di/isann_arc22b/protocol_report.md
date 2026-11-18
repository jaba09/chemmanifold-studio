# Protocolo CFD: isann_arc22b

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
| **Media abs dT en la llama** (T > 1600 K) | **5.2 K** (sesgo +1.9 K) |
| Deriva de ese error (100-150 ms) | +2.05 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 9.4 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 6.7 / 8.2 / 5.5 / 9.9 K |
| p95 abs dT, celdas calientes | 21 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 5 % / 3 %, ×1.01 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 11 % / 7 %, ×1.01 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 4 % / 7 %, ×1.01 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 8 %, ×1.06 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.09 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 6 % / 6 % |
| Error L1 del campo de calor liberado (celdas calientes) | 18 % |
| GA18 / OOD | – / – |
| Coste | 6.47 s por paso (None procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 75132 (0) | 0.044 | 8 % | 6 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4349 | 0.0 | -0.0 | 0.1 | 0.2 | 0 % | 0 % | 1.00 | 1.00 | 2114 / 2114 |
| 105.0 | llama | 4273 | 0.0 | -0.0 | 0.1 | 0.2 | 0 % | 0 % | 1.00 | 1.00 | 2114 / 2114 |
| 107.5 | llama | 4224 | 0.1 | -0.0 | 0.1 | 0.2 | 0 % | 0 % | 1.00 | 1.00 | 2114 / 2114 |
| 110.0 | llama | 4214 | 2.6 | +2.3 | 2.1 | 3.6 | 4 % | 2 % | 1.00 | 0.96 | 2113 / 2115 |
| 112.5 | llama | 4199 | 3.2 | +1.1 | 3.4 | 5.1 | 4 % | 7 % | 1.00 | 1.04 | 2113 / 2112 |
| 115.0 | llama | 4191 | 4.0 | -0.1 | 4.1 | 5.6 | 4 % | 8 % | 1.00 | 1.03 | 2113 / 2110 |
| 117.5 | llama | 4194 | 4.5 | -0.7 | 5.0 | 6.4 | 4 % | 9 % | 1.00 | 1.04 | 2112 / 2110 |
| 120.0 | llama | 4186 | 4.6 | -0.7 | 5.7 | 7.1 | 4 % | 10 % | 1.00 | 1.04 | 2112 / 2110 |
| 122.5 | llama | 4191 | 4.9 | -0.6 | 6.5 | 8.0 | 4 % | 12 % | 1.00 | 1.05 | 2112 / 2110 |
| 125.0 | llama | 4188 | 5.0 | -0.0 | 6.9 | 9.0 | 4 % | 13 % | 1.00 | 1.05 | 2111 / 2111 |
| 127.5 | llama | 4187 | 5.3 | +0.7 | 7.3 | 9.9 | 4 % | 14 % | 1.00 | 1.05 | 2111 / 2112 |
| 130.0 | llama | 4187 | 5.4 | +1.1 | 7.5 | 10.5 | 4 % | 15 % | 1.00 | 1.04 | 2110 / 2112 |
| 132.5 | llama | 4202 | 5.4 | +1.3 | 7.7 | 11.0 | 5 % | 16 % | 1.00 | 1.04 | 2109 / 2111 |
| 135.0 | llama | 4203 | 5.8 | +1.6 | 8.0 | 11.5 | 5 % | 16 % | 1.01 | 1.04 | 2109 / 2111 |
| 137.5 | llama | 4206 | 6.0 | +1.8 | 8.3 | 11.6 | 5 % | 16 % | 1.01 | 1.31 | 2108 / 2110 |
| 140.0 | llama | 4248 | 7.5 | +4.5 | 9.9 | 14.3 | 6 % | 15 % | 1.01 | 1.20 | 2108 / 2112 |
| 142.5 | llama | 4259 | 8.5 | +5.4 | 11.5 | 15.8 | 8 % | 16 % | 1.02 | 1.24 | 2108 / 2112 |
| 145.0 | llama | 4266 | 9.6 | +6.1 | 12.3 | 17.2 | 9 % | 17 % | 1.02 | 1.27 | 2107 / 2112 |
| 147.5 | llama | 4270 | 10.3 | +6.8 | 13.0 | 18.0 | 10 % | 18 % | 1.03 | 1.20 | 2107 / 2111 |
| 150.0 | llama | 4274 | 10.8 | +7.1 | 13.6 | 18.5 | 10 % | 18 % | 1.03 | 1.19 | 2106 / 2109 |
