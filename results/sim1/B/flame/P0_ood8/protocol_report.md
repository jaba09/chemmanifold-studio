# Protocolo CFD: P0_ood8

Modo: **pure**. Modelo: `/opt/ofb/models/P0_ood8`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **7.8 K** (sesgo -3.6 K) |
| Deriva de ese error (100-150 ms) | +0.07 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 7.9 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 6.5 / 5.2 / 5.9 / 11.8 K |
| p95 abs dT, celdas calientes | 19 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 16 %, ×1.17 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 4 % / 3 %, ×0.97 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 5 %, ×0.98 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 19 % / 18 %, ×1.09 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.26 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 13 % |
| Error L1 del campo de calor liberado (celdas calientes) | 215 % |
| GA18 / OOD | 0.0 % / 8.9 % |
| Coste | 4.09 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 24703 (3100) | 0.0294 | 6 % | 23 % | 6 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4519 | 7.2 | -3.4 | 3.9 | 7.7 | 16 % | 2 % | 1.00 | 3.33 | 2123 / 2118 |
| 105.0 | llama | 4528 | 7.8 | -3.5 | 5.2 | 9.7 | 17 % | 3 % | 1.00 | 3.31 | 2123 / 2118 |
| 107.5 | llama | 4528 | 7.8 | -3.5 | 5.6 | 10.5 | 18 % | 3 % | 1.00 | 3.31 | 2123 / 2119 |
| 110.0 | llama | 4529 | 7.8 | -3.5 | 5.8 | 10.8 | 18 % | 3 % | 1.00 | 3.30 | 2123 / 2119 |
| 112.5 | llama | 4527 | 7.7 | -3.5 | 6.0 | 10.9 | 18 % | 4 % | 1.00 | 3.29 | 2123 / 2119 |
| 115.0 | llama | 4532 | 7.6 | -3.5 | 6.2 | 11.0 | 18 % | 4 % | 1.00 | 3.28 | 2123 / 2119 |
| 117.5 | llama | 4531 | 7.7 | -3.5 | 6.4 | 11.2 | 19 % | 4 % | 1.00 | 3.28 | 2123 / 2120 |
| 120.0 | llama | 4538 | 7.7 | -3.5 | 6.6 | 11.3 | 19 % | 4 % | 1.00 | 3.27 | 2123 / 2120 |
| 122.5 | llama | 4536 | 7.7 | -3.4 | 6.7 | 11.4 | 19 % | 4 % | 1.00 | 3.27 | 2123 / 2120 |
| 125.0 | llama | 4545 | 7.7 | -3.4 | 6.8 | 11.4 | 19 % | 4 % | 1.00 | 3.26 | 2123 / 2120 |
| 127.5 | llama | 4547 | 7.8 | -3.4 | 6.9 | 11.4 | 19 % | 5 % | 1.00 | 3.26 | 2123 / 2120 |
| 130.0 | llama | 4551 | 7.8 | -3.5 | 7.0 | 11.2 | 19 % | 5 % | 1.00 | 3.25 | 2123 / 2121 |
| 132.5 | llama | 4556 | 7.9 | -3.5 | 7.0 | 11.0 | 19 % | 5 % | 1.00 | 3.25 | 2123 / 2121 |
| 135.0 | llama | 4555 | 7.9 | -3.6 | 7.0 | 10.9 | 19 % | 5 % | 1.00 | 3.24 | 2123 / 2120 |
| 137.5 | llama | 4556 | 7.9 | -3.6 | 7.0 | 11.0 | 19 % | 5 % | 1.00 | 3.23 | 2122 / 2120 |
| 140.0 | llama | 4557 | 7.9 | -3.6 | 7.0 | 11.1 | 19 % | 5 % | 1.00 | 3.23 | 2122 / 2120 |
| 142.5 | llama | 4554 | 7.9 | -3.7 | 7.0 | 11.3 | 19 % | 5 % | 1.00 | 3.22 | 2122 / 2119 |
| 145.0 | llama | 4547 | 7.8 | -3.7 | 7.1 | 11.6 | 19 % | 6 % | 1.00 | 3.22 | 2121 / 2119 |
| 147.5 | llama | 4546 | 7.8 | -3.8 | 7.2 | 11.9 | 19 % | 6 % | 1.00 | 3.22 | 2121 / 2118 |
| 150.0 | llama | 4543 | 7.9 | -3.9 | 7.4 | 12.2 | 19 % | 6 % | 1.00 | 3.22 | 2121 / 2118 |
