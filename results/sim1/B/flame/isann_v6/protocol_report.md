# Protocolo CFD: isann_v6

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/isann_v6`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **5.8 K** (sesgo +3.6 K) |
| Deriva de ese error (100-150 ms) | +0.23 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 6.2 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 6.1 / 6.8 / 6.1 / 3.6 K |
| p95 abs dT, celdas calientes | 16 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 11 % / 9 %, ×0.97 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 14 % / 6 %, ×0.93 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 4 %, ×1.02 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 21 % / 19 %, ×0.86 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.88 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 10 % |
| Error L1 del campo de calor liberado (celdas calientes) | 43 % |
| GA18 / OOD | 0.0 % / 2.8 % |
| Coste | 2.09 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 25899 (2302) | 0.0511 | 8 % | 12 % | 10 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4532 | 4.4 | +3.2 | 3.0 | 3.8 | 9 % | 5 % | 1.00 | 0.86 | 2123 / 2130 |
| 105.0 | llama | 4545 | 5.3 | +3.7 | 4.3 | 5.1 | 10 % | 7 % | 1.00 | 0.87 | 2123 / 2130 |
| 107.5 | llama | 4553 | 5.6 | +3.9 | 4.9 | 5.7 | 10 % | 9 % | 1.00 | 0.87 | 2123 / 2130 |
| 110.0 | llama | 4555 | 5.7 | +3.8 | 5.3 | 5.9 | 10 % | 11 % | 1.00 | 0.87 | 2123 / 2130 |
| 112.5 | llama | 4559 | 5.7 | +3.7 | 5.5 | 6.0 | 10 % | 12 % | 1.00 | 0.87 | 2123 / 2130 |
| 115.0 | llama | 4571 | 5.7 | +3.6 | 5.7 | 6.0 | 11 % | 12 % | 0.99 | 0.87 | 2123 / 2131 |
| 117.5 | llama | 4576 | 5.7 | +3.5 | 5.8 | 5.9 | 11 % | 13 % | 1.00 | 0.87 | 2123 / 2131 |
| 120.0 | llama | 4582 | 5.8 | +3.4 | 6.0 | 5.8 | 11 % | 14 % | 1.00 | 0.87 | 2123 / 2131 |
| 122.5 | llama | 4584 | 5.8 | +3.4 | 6.1 | 5.8 | 11 % | 14 % | 0.99 | 0.87 | 2123 / 2131 |
| 125.0 | llama | 4590 | 5.9 | +3.4 | 6.1 | 5.7 | 12 % | 15 % | 0.99 | 0.88 | 2123 / 2131 |
| 127.5 | llama | 4588 | 5.9 | +3.4 | 6.2 | 5.6 | 12 % | 15 % | 0.99 | 0.88 | 2123 / 2131 |
| 130.0 | llama | 4595 | 6.0 | +3.5 | 6.3 | 5.6 | 12 % | 15 % | 0.99 | 0.88 | 2123 / 2131 |
| 132.5 | llama | 4596 | 6.0 | +3.5 | 6.4 | 5.7 | 12 % | 16 % | 0.99 | 0.88 | 2123 / 2131 |
| 135.0 | llama | 4595 | 6.0 | +3.5 | 6.6 | 5.8 | 12 % | 16 % | 0.99 | 0.89 | 2123 / 2130 |
| 137.5 | llama | 4597 | 6.0 | +3.6 | 6.8 | 6.0 | 12 % | 17 % | 0.99 | 0.89 | 2122 / 2130 |
| 140.0 | llama | 4593 | 6.1 | +3.6 | 7.0 | 6.1 | 12 % | 18 % | 0.99 | 0.89 | 2122 / 2130 |
| 142.5 | llama | 4594 | 6.1 | +3.6 | 7.3 | 6.3 | 12 % | 19 % | 1.00 | 0.89 | 2122 / 2130 |
| 145.0 | llama | 4589 | 6.1 | +3.6 | 7.6 | 6.4 | 12 % | 19 % | 1.00 | 0.89 | 2121 / 2129 |
| 147.5 | llama | 4584 | 6.2 | +3.6 | 7.9 | 6.6 | 12 % | 20 % | 1.00 | 0.89 | 2121 / 2129 |
| 150.0 | llama | 4578 | 6.3 | +3.6 | 8.2 | 6.7 | 12 % | 20 % | 1.00 | 0.89 | 2121 / 2129 |
