# Protocolo CFD: isann_D

Modo: **pure**. Modelo: `/opt/ofb/models/isann_D`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **5.2 K** (sesgo +4.5 K) |
| Deriva de ese error (100-150 ms) | +0.43 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 5.7 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 4.7 / 4.3 / 4.5 / 5.8 K |
| p95 abs dT, celdas calientes | 12 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 2 %, ×1.01 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 6 %, ×0.95 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 4 %, ×1.01 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 5 % / 4 %, ×1.00 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.06 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 8 % |
| Error L1 del campo de calor liberado (celdas calientes) | 15 % |
| GA18 / OOD | 0.0 % / 0.0 % |
| Coste | 1.94 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 22664 (0) | 0.0189 | 3 % | 2 % | 5 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4521 | 2.6 | +2.1 | 1.9 | 2.3 | 2 % | 3 % | 1.00 | 1.07 | 2123 / 2121 |
| 105.0 | llama | 4541 | 3.7 | +3.2 | 2.9 | 3.7 | 2 % | 4 % | 1.00 | 1.07 | 2123 / 2121 |
| 107.5 | llama | 4553 | 4.4 | +3.9 | 3.6 | 4.7 | 3 % | 5 % | 1.00 | 1.07 | 2123 / 2121 |
| 110.0 | llama | 4557 | 4.8 | +4.3 | 4.2 | 5.2 | 3 % | 6 % | 1.01 | 1.07 | 2123 / 2121 |
| 112.5 | llama | 4577 | 5.1 | +4.6 | 4.6 | 5.5 | 3 % | 6 % | 1.01 | 1.07 | 2123 / 2121 |
| 115.0 | llama | 4586 | 5.2 | +4.7 | 4.8 | 5.9 | 3 % | 7 % | 1.00 | 1.07 | 2123 / 2121 |
| 117.5 | llama | 4595 | 5.3 | +4.7 | 4.8 | 6.2 | 3 % | 7 % | 1.01 | 1.07 | 2123 / 2121 |
| 120.0 | llama | 4601 | 5.4 | +4.8 | 4.8 | 6.4 | 3 % | 7 % | 1.01 | 1.07 | 2123 / 2121 |
| 122.5 | llama | 4603 | 5.4 | +4.7 | 4.9 | 6.5 | 3 % | 7 % | 1.01 | 1.07 | 2123 / 2121 |
| 125.0 | llama | 4606 | 5.4 | +4.7 | 4.9 | 6.6 | 3 % | 7 % | 1.01 | 1.07 | 2123 / 2121 |
| 127.5 | llama | 4608 | 5.4 | +4.7 | 4.9 | 6.7 | 3 % | 8 % | 1.01 | 1.07 | 2123 / 2121 |
| 130.0 | llama | 4610 | 5.5 | +4.7 | 5.0 | 6.8 | 3 % | 8 % | 1.01 | 1.07 | 2123 / 2121 |
| 132.5 | llama | 4606 | 5.5 | +4.7 | 5.0 | 6.9 | 3 % | 8 % | 1.01 | 1.06 | 2123 / 2121 |
| 135.0 | llama | 4610 | 5.5 | +4.7 | 5.1 | 7.1 | 3 % | 8 % | 1.01 | 1.06 | 2123 / 2121 |
| 137.5 | llama | 4610 | 5.6 | +4.7 | 5.2 | 7.2 | 3 % | 8 % | 1.01 | 1.06 | 2122 / 2121 |
| 140.0 | llama | 4613 | 5.6 | +4.8 | 5.3 | 7.2 | 4 % | 8 % | 1.01 | 1.05 | 2122 / 2120 |
| 142.5 | llama | 4607 | 5.7 | +4.8 | 5.4 | 7.3 | 4 % | 8 % | 1.01 | 1.05 | 2122 / 2120 |
| 145.0 | llama | 4608 | 5.8 | +4.9 | 5.5 | 7.2 | 4 % | 8 % | 1.01 | 1.05 | 2121 / 2120 |
| 147.5 | llama | 4603 | 5.8 | +5.0 | 5.6 | 7.2 | 4 % | 8 % | 1.01 | 1.05 | 2121 / 2119 |
| 150.0 | llama | 4597 | 5.9 | +5.0 | 5.7 | 7.1 | 4 % | 8 % | 1.01 | 1.05 | 2121 / 2119 |
