# Protocolo CFD: isann_D_online

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
| **Media abs dT en la llama** (T > 1600 K) | **5.2 K** (sesgo +3.8 K) |
| Deriva de ese error (100-150 ms) | +0.31 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 5.7 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 6.8 / 7.6 / 7.5 / 7.3 K |
| p95 abs dT, celdas calientes | 20 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 4 % / 3 %, ×0.99 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 10 % / 7 %, ×0.92 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 4 %, ×1.02 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 6 % / 5 %, ×0.97 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.07 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 8 % |
| Error L1 del campo de calor liberado (celdas calientes) | 19 % |
| GA18 / OOD | – / – |
| Coste | 2.11 s por paso (None procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 109303 (0) | 0.0245 | 4 % | 2 % | 6 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4529 | 3.9 | +3.4 | 2.8 | 3.0 | 5 % | 6 % | 1.00 | 1.01 | 2123 / 2127 |
| 105.0 | llama | 4539 | 4.9 | +4.3 | 3.9 | 3.7 | 6 % | 10 % | 1.01 | 1.01 | 2123 / 2127 |
| 107.5 | llama | 4550 | 5.3 | +4.7 | 4.8 | 5.1 | 6 % | 12 % | 1.00 | 1.00 | 2123 / 2127 |
| 110.0 | llama | 4556 | 4.8 | +3.8 | 4.9 | 5.5 | 4 % | 12 % | 1.00 | 1.07 | 2123 / 2124 |
| 112.5 | llama | 4570 | 4.6 | +3.3 | 5.1 | 5.8 | 4 % | 11 % | 1.00 | 1.07 | 2123 / 2123 |
| 115.0 | llama | 4584 | 4.4 | +2.9 | 5.7 | 6.2 | 3 % | 11 % | 1.00 | 1.08 | 2123 / 2123 |
| 117.5 | llama | 4597 | 4.6 | +3.0 | 7.3 | 7.4 | 3 % | 11 % | 1.00 | 1.08 | 2123 / 2123 |
| 120.0 | llama | 4610 | 4.8 | +2.7 | 8.5 | 8.3 | 3 % | 11 % | 1.00 | 1.10 | 2123 / 2122 |
| 122.5 | llama | 4609 | 5.0 | +2.3 | 9.1 | 8.2 | 3 % | 10 % | 1.00 | 1.11 | 2123 / 2120 |
| 125.0 | llama | 4614 | 5.1 | +2.6 | 8.8 | 7.8 | 3 % | 10 % | 1.00 | 1.11 | 2123 / 2120 |
| 127.5 | llama | 4617 | 5.2 | +2.9 | 8.2 | 7.3 | 3 % | 10 % | 1.00 | 1.12 | 2123 / 2119 |
| 130.0 | llama | 4620 | 5.3 | +3.6 | 8.1 | 6.8 | 3 % | 9 % | 1.00 | 1.10 | 2123 / 2120 |
| 132.5 | llama | 4628 | 5.5 | +4.0 | 7.9 | 6.5 | 3 % | 9 % | 1.00 | 1.09 | 2123 / 2120 |
| 135.0 | llama | 4628 | 5.5 | +4.2 | 7.7 | 6.3 | 3 % | 9 % | 1.01 | 1.09 | 2123 / 2120 |
| 137.5 | llama | 4629 | 5.6 | +4.3 | 7.6 | 6.1 | 3 % | 9 % | 1.01 | 1.09 | 2122 / 2120 |
| 140.0 | llama | 4620 | 5.5 | +4.4 | 7.4 | 6.0 | 3 % | 9 % | 1.01 | 1.08 | 2122 / 2119 |
| 142.5 | llama | 4613 | 5.7 | +4.7 | 7.0 | 6.3 | 3 % | 9 % | 1.01 | 1.05 | 2122 / 2120 |
| 145.0 | llama | 4611 | 5.8 | +4.8 | 6.9 | 6.6 | 3 % | 9 % | 1.01 | 1.05 | 2121 / 2119 |
| 147.5 | llama | 4603 | 5.8 | +4.9 | 6.9 | 6.9 | 3 % | 9 % | 1.01 | 1.05 | 2121 / 2119 |
| 150.0 | llama | 4599 | 5.8 | +4.9 | 7.0 | 7.1 | 3 % | 9 % | 1.00 | 1.05 | 2121 / 2119 |
