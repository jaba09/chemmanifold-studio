# Protocolo CFD: isat1e-4

Modo: **di**. Modelo: `GA18 (DI)`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **0.9 K** (sesgo -0.5 K) |
| Deriva de ese error (100-150 ms) | +0.17 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 1.1 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.2 / 0.8 / 2.0 / 1.1 K |
| p95 abs dT, celdas calientes | 4 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 1 %, ×1.00 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 0 % / 0 %, ×1.00 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 0 % / 0 %, ×1.00 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 1 %, ×1.00 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.00 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 7 % |
| Error L1 del campo de calor liberado (celdas calientes) | 2 % |
| GA18 / OOD | – / – |
| Coste | 3.65 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4503 | 0.3 | -0.1 | 0.4 | 0.3 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 105.0 | llama | 4508 | 0.4 | -0.2 | 0.6 | 0.4 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 107.5 | llama | 4510 | 0.5 | -0.3 | 0.7 | 0.6 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 110.0 | llama | 4512 | 0.6 | -0.3 | 0.7 | 0.7 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 112.5 | llama | 4516 | 0.7 | -0.3 | 0.8 | 0.9 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 115.0 | llama | 4518 | 0.7 | -0.4 | 0.9 | 1.0 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 117.5 | llama | 4516 | 0.8 | -0.4 | 1.0 | 1.1 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 120.0 | llama | 4524 | 0.8 | -0.4 | 1.1 | 1.2 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 122.5 | llama | 4522 | 0.9 | -0.5 | 1.1 | 1.3 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 125.0 | llama | 4534 | 0.9 | -0.5 | 1.2 | 1.4 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 127.5 | llama | 4535 | 1.0 | -0.6 | 1.3 | 1.4 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 130.0 | llama | 4541 | 1.0 | -0.6 | 1.4 | 1.4 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2122 |
| 132.5 | llama | 4541 | 1.1 | -0.6 | 1.4 | 1.4 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2122 |
| 135.0 | llama | 4543 | 1.1 | -0.7 | 1.5 | 1.5 | 1 % | 0 % | 1.00 | 1.00 | 2123 / 2122 |
| 137.5 | llama | 4543 | 1.2 | -0.7 | 1.5 | 1.5 | 1 % | 0 % | 1.00 | 1.00 | 2122 / 2122 |
| 140.0 | llama | 4543 | 1.2 | -0.6 | 1.6 | 1.5 | 1 % | 0 % | 1.00 | 0.99 | 2122 / 2121 |
| 142.5 | llama | 4544 | 1.2 | -0.6 | 1.6 | 1.6 | 1 % | 0 % | 1.00 | 1.00 | 2122 / 2121 |
| 145.0 | llama | 4537 | 1.2 | -0.6 | 1.6 | 1.6 | 1 % | 0 % | 1.00 | 1.00 | 2121 / 2121 |
| 147.5 | llama | 4536 | 1.1 | -0.5 | 1.6 | 1.6 | 1 % | 0 % | 0.99 | 1.00 | 2121 / 2121 |
| 150.0 | llama | 4530 | 1.1 | -0.5 | 1.6 | 1.6 | 1 % | 0 % | 1.00 | 1.00 | 2121 / 2121 |
