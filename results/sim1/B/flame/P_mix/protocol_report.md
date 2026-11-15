# Protocolo CFD: P_mix

Modo: **pure**. Modelo: `/opt/ofb/models/P_mix`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **10.3 K** (sesgo -7.2 K) |
| Deriva de ese error (100-150 ms) | +0.47 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 11.2 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 8.3 / 8.8 / 5.6 / 7.5 K |
| p95 abs dT, celdas calientes | 24 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 19 % / 20 %, ×1.18 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 6 % / 3 %, ×1.02 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 6 %, ×0.98 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 16 %, ×1.03 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×4.18 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 10 % |
| Error L1 del campo de calor liberado (celdas calientes) | 295 % |
| GA18 / OOD | 0.0 % / 7.0 % |
| Coste | 7.12 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 24635 (2476) | 0.0192 | 4 % | 4 % | 2 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4515 | 8.4 | -6.1 | 4.0 | 7.9 | 19 % | 3 % | 1.00 | 4.27 | 2123 / 2118 |
| 105.0 | llama | 4523 | 9.3 | -6.5 | 5.0 | 10.0 | 19 % | 3 % | 1.00 | 4.25 | 2123 / 2119 |
| 107.5 | llama | 4524 | 9.6 | -6.7 | 5.5 | 10.9 | 19 % | 4 % | 1.00 | 4.23 | 2123 / 2119 |
| 110.0 | llama | 4523 | 9.7 | -6.8 | 5.8 | 11.4 | 19 % | 4 % | 1.00 | 4.22 | 2123 / 2119 |
| 112.5 | llama | 4524 | 9.8 | -6.9 | 6.1 | 11.7 | 19 % | 4 % | 1.00 | 4.22 | 2123 / 2119 |
| 115.0 | llama | 4528 | 9.9 | -7.0 | 6.4 | 11.9 | 19 % | 5 % | 1.00 | 4.21 | 2123 / 2120 |
| 117.5 | llama | 4528 | 10.0 | -7.0 | 6.8 | 12.0 | 19 % | 5 % | 1.00 | 4.20 | 2123 / 2120 |
| 120.0 | llama | 4534 | 10.0 | -7.1 | 7.2 | 12.1 | 19 % | 5 % | 1.00 | 4.20 | 2123 / 2120 |
| 122.5 | llama | 4534 | 10.2 | -7.2 | 7.6 | 12.2 | 19 % | 5 % | 0.99 | 4.19 | 2123 / 2121 |
| 125.0 | llama | 4544 | 10.3 | -7.3 | 8.1 | 12.2 | 19 % | 5 % | 0.99 | 4.18 | 2123 / 2121 |
| 127.5 | llama | 4545 | 10.4 | -7.5 | 8.8 | 12.2 | 19 % | 6 % | 0.99 | 4.18 | 2123 / 2121 |
| 130.0 | llama | 4549 | 10.4 | -7.6 | 9.6 | 12.3 | 19 % | 6 % | 0.99 | 4.17 | 2123 / 2121 |
| 132.5 | llama | 4550 | 10.3 | -7.7 | 10.2 | 12.3 | 19 % | 7 % | 0.99 | 4.16 | 2123 / 2121 |
| 135.0 | llama | 4550 | 10.4 | -7.7 | 10.6 | 12.4 | 19 % | 7 % | 0.99 | 4.16 | 2123 / 2121 |
| 137.5 | llama | 4550 | 10.5 | -7.7 | 10.8 | 12.6 | 19 % | 8 % | 0.99 | 4.15 | 2122 / 2120 |
| 140.0 | llama | 4553 | 10.7 | -7.7 | 10.8 | 12.9 | 19 % | 8 % | 0.99 | 4.14 | 2122 / 2120 |
| 142.5 | llama | 4553 | 11.0 | -7.6 | 10.8 | 13.2 | 19 % | 8 % | 0.99 | 4.14 | 2122 / 2120 |
| 145.0 | llama | 4549 | 11.2 | -7.5 | 10.6 | 13.4 | 19 % | 8 % | 0.99 | 4.13 | 2121 / 2120 |
| 147.5 | llama | 4550 | 11.4 | -7.4 | 10.5 | 13.7 | 19 % | 8 % | 0.99 | 4.13 | 2121 / 2120 |
| 150.0 | llama | 4542 | 11.6 | -7.4 | 10.5 | 13.8 | 19 % | 8 % | 0.99 | 4.13 | 2121 / 2119 |
