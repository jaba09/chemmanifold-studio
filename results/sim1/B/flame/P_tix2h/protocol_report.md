# Protocolo CFD: P_tix2h

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2h`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **14.9 K** (sesgo -13.0 K) |
| Deriva de ese error (100-150 ms) | +0.67 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 15.9 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 8.2 / 5.3 / 5.3 / 4.4 K |
| p95 abs dT, celdas calientes | 22 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 23 % / 24 %, ×1.23 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 7 %, ×1.03 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 7 %, ×0.98 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 19 % / 18 %, ×1.02 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×5.18 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 11 % |
| Error L1 del campo de calor liberado (celdas calientes) | 386 % |
| GA18 / OOD | 0.0 % / 0.8 % |
| Coste | 3.95 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 25164 (1051) | 0.0366 | 7 % | 3 % | 7 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4513 | 11.5 | -10.5 | 5.2 | 9.6 | 23 % | 4 % | 1.00 | 5.28 | 2123 / 2116 |
| 105.0 | llama | 4521 | 13.2 | -11.3 | 6.5 | 12.0 | 23 % | 6 % | 1.00 | 5.26 | 2123 / 2116 |
| 107.5 | llama | 4522 | 13.9 | -11.8 | 7.2 | 13.2 | 23 % | 6 % | 1.00 | 5.24 | 2123 / 2117 |
| 110.0 | llama | 4525 | 14.2 | -12.1 | 7.5 | 13.7 | 23 % | 7 % | 1.00 | 5.23 | 2123 / 2117 |
| 112.5 | llama | 4526 | 14.4 | -12.3 | 7.7 | 14.0 | 24 % | 7 % | 1.00 | 5.22 | 2123 / 2117 |
| 115.0 | llama | 4525 | 14.5 | -12.6 | 7.9 | 14.2 | 24 % | 7 % | 1.00 | 5.21 | 2123 / 2117 |
| 117.5 | llama | 4531 | 14.6 | -12.7 | 8.0 | 14.5 | 24 % | 7 % | 1.00 | 5.20 | 2123 / 2117 |
| 120.0 | llama | 4533 | 14.7 | -12.9 | 8.1 | 14.7 | 24 % | 7 % | 1.00 | 5.20 | 2123 / 2117 |
| 122.5 | llama | 4536 | 14.8 | -13.0 | 8.3 | 14.9 | 24 % | 7 % | 0.99 | 5.19 | 2123 / 2117 |
| 125.0 | llama | 4545 | 14.9 | -13.2 | 8.4 | 15.1 | 24 % | 7 % | 0.99 | 5.18 | 2123 / 2117 |
| 127.5 | llama | 4548 | 15.1 | -13.3 | 8.5 | 15.2 | 24 % | 7 % | 0.99 | 5.17 | 2123 / 2117 |
| 130.0 | llama | 4551 | 15.2 | -13.4 | 8.6 | 15.2 | 23 % | 7 % | 0.99 | 5.17 | 2123 / 2117 |
| 132.5 | llama | 4554 | 15.4 | -13.5 | 8.7 | 15.1 | 23 % | 7 % | 0.99 | 5.16 | 2123 / 2116 |
| 135.0 | llama | 4554 | 15.5 | -13.7 | 8.8 | 15.2 | 23 % | 7 % | 0.99 | 5.15 | 2123 / 2116 |
| 137.5 | llama | 4554 | 15.6 | -13.8 | 8.9 | 15.3 | 23 % | 7 % | 0.99 | 5.14 | 2122 / 2116 |
| 140.0 | llama | 4556 | 15.7 | -13.9 | 9.0 | 15.4 | 23 % | 7 % | 0.99 | 5.12 | 2122 / 2116 |
| 142.5 | llama | 4551 | 15.8 | -14.0 | 9.1 | 15.4 | 23 % | 7 % | 0.99 | 5.11 | 2122 / 2115 |
| 145.0 | llama | 4545 | 15.9 | -14.1 | 9.1 | 15.4 | 23 % | 7 % | 0.99 | 5.10 | 2121 / 2115 |
| 147.5 | llama | 4544 | 16.0 | -14.3 | 9.2 | 15.4 | 23 % | 7 % | 0.99 | 5.10 | 2121 / 2114 |
| 150.0 | llama | 4540 | 16.2 | -14.4 | 9.2 | 15.4 | 23 % | 7 % | 0.99 | 5.09 | 2121 / 2114 |
