# Protocolo CFD: P_tix2c

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2c`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **8.0 K** (sesgo -3.7 K) |
| Deriva de ese error (100-150 ms) | +0.53 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 8.8 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 5.2 / 3.4 / 4.2 / 6.9 K |
| p95 abs dT, celdas calientes | 13 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 10 % / 9 %, ×1.05 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 6 % / 5 %, ×1.03 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 2 %, ×0.99 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 24 % / 23 %, ×0.87 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.08 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 8 % |
| Error L1 del campo de calor liberado (celdas calientes) | 199 % |
| GA18 / OOD | 0.0 % / 2.6 % |
| Coste | 3.66 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 23301 (1200) | 0.025 | 4 % | 7 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4512 | 5.8 | -2.8 | 2.8 | 4.2 | 10 % | 3 % | 1.00 | 3.10 | 2123 / 2125 |
| 105.0 | llama | 4518 | 6.7 | -3.1 | 3.5 | 5.2 | 10 % | 4 % | 1.00 | 3.10 | 2123 / 2125 |
| 107.5 | llama | 4523 | 7.1 | -3.3 | 3.8 | 5.8 | 10 % | 5 % | 1.00 | 3.10 | 2123 / 2125 |
| 110.0 | llama | 4524 | 7.3 | -3.4 | 4.1 | 6.2 | 10 % | 5 % | 1.00 | 3.10 | 2123 / 2126 |
| 112.5 | llama | 4524 | 7.4 | -3.5 | 4.3 | 6.5 | 10 % | 6 % | 1.00 | 3.09 | 2123 / 2126 |
| 115.0 | llama | 4523 | 7.5 | -3.6 | 4.4 | 6.5 | 10 % | 6 % | 1.00 | 3.09 | 2123 / 2126 |
| 117.5 | llama | 4525 | 7.6 | -3.7 | 4.6 | 6.7 | 10 % | 6 % | 1.00 | 3.09 | 2123 / 2126 |
| 120.0 | llama | 4533 | 7.8 | -3.7 | 4.8 | 6.9 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2126 |
| 122.5 | llama | 4530 | 8.0 | -3.7 | 5.0 | 7.2 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2125 |
| 125.0 | llama | 4540 | 8.1 | -3.7 | 5.3 | 7.6 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2125 |
| 127.5 | llama | 4547 | 8.2 | -3.8 | 5.5 | 7.9 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2125 |
| 130.0 | llama | 4552 | 8.4 | -3.8 | 5.7 | 8.2 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2125 |
| 132.5 | llama | 4552 | 8.5 | -3.8 | 5.9 | 8.3 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2125 |
| 135.0 | llama | 4554 | 8.6 | -3.9 | 6.2 | 8.4 | 10 % | 6 % | 1.00 | 3.08 | 2123 / 2125 |
| 137.5 | llama | 4554 | 8.6 | -3.9 | 6.4 | 8.4 | 10 % | 6 % | 1.00 | 3.08 | 2122 / 2124 |
| 140.0 | llama | 4557 | 8.7 | -3.9 | 6.5 | 8.3 | 10 % | 7 % | 1.00 | 3.08 | 2122 / 2124 |
| 142.5 | llama | 4553 | 8.7 | -3.9 | 6.5 | 8.3 | 10 % | 7 % | 1.00 | 3.07 | 2122 / 2124 |
| 145.0 | llama | 4549 | 8.8 | -3.9 | 6.5 | 8.1 | 10 % | 7 % | 1.00 | 3.07 | 2121 / 2123 |
| 147.5 | llama | 4548 | 8.8 | -3.9 | 6.5 | 8.0 | 10 % | 7 % | 1.00 | 3.07 | 2121 / 2123 |
| 150.0 | llama | 4542 | 8.9 | -3.9 | 6.5 | 7.8 | 10 % | 7 % | 1.00 | 3.07 | 2121 / 2122 |
