# Protocolo CFD: isat1e-3

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
| **Media abs dT en la llama** (T > 1600 K) | **2.9 K** (sesgo +1.5 K) |
| Deriva de ese error (100-150 ms) | +0.52 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 3.7 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 3.1 / 2.0 / 4.9 / 1.4 K |
| p95 abs dT, celdas calientes | 10 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 2 %, ×1.01 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 1 %, ×1.00 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 0 % / 1 %, ×1.00 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 2 %, ×1.01 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.99 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 7 % |
| Error L1 del campo de calor liberado (celdas calientes) | 7 % |
| GA18 / OOD | – / – |
| Coste | 2.96 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4513 | 1.0 | +0.6 | 0.9 | 1.1 | 1 % | 0 % | 1.00 | 0.98 | 2123 / 2123 |
| 105.0 | llama | 4521 | 1.6 | +0.9 | 1.3 | 1.7 | 2 % | 0 % | 1.00 | 0.99 | 2123 / 2124 |
| 107.5 | llama | 4526 | 1.8 | +1.0 | 1.7 | 2.0 | 2 % | 0 % | 1.01 | 0.99 | 2123 / 2123 |
| 110.0 | llama | 4529 | 2.0 | +1.1 | 2.0 | 2.4 | 2 % | 1 % | 1.00 | 1.01 | 2123 / 2124 |
| 112.5 | llama | 4531 | 2.3 | +1.2 | 2.3 | 2.8 | 3 % | 1 % | 1.00 | 0.99 | 2123 / 2124 |
| 115.0 | llama | 4536 | 2.4 | +1.3 | 2.5 | 3.1 | 2 % | 1 % | 1.01 | 0.99 | 2123 / 2124 |
| 117.5 | llama | 4538 | 2.6 | +1.3 | 2.7 | 3.4 | 3 % | 1 % | 1.01 | 0.99 | 2123 / 2124 |
| 120.0 | llama | 4548 | 2.8 | +1.3 | 3.0 | 3.8 | 3 % | 1 % | 1.01 | 0.99 | 2123 / 2124 |
| 122.5 | llama | 4545 | 2.9 | +1.4 | 3.3 | 4.0 | 3 % | 1 % | 1.01 | 0.97 | 2123 / 2124 |
| 125.0 | llama | 4552 | 3.0 | +1.4 | 3.4 | 4.3 | 3 % | 1 % | 1.01 | 0.99 | 2123 / 2124 |
| 127.5 | llama | 4559 | 3.0 | +1.5 | 3.5 | 4.4 | 2 % | 1 % | 1.01 | 0.99 | 2123 / 2124 |
| 130.0 | llama | 4562 | 3.1 | +1.6 | 3.5 | 4.6 | 3 % | 1 % | 1.01 | 1.00 | 2123 / 2124 |
| 132.5 | llama | 4564 | 3.2 | +1.7 | 3.6 | 4.7 | 3 % | 1 % | 1.01 | 0.98 | 2123 / 2124 |
| 135.0 | llama | 4566 | 3.3 | +1.7 | 3.7 | 4.7 | 3 % | 1 % | 1.01 | 0.99 | 2123 / 2124 |
| 137.5 | llama | 4568 | 3.5 | +1.8 | 3.8 | 4.8 | 3 % | 1 % | 1.01 | 0.98 | 2122 / 2124 |
| 140.0 | llama | 4568 | 3.5 | +1.8 | 3.8 | 4.7 | 3 % | 1 % | 1.01 | 0.98 | 2122 / 2123 |
| 142.5 | llama | 4563 | 3.6 | +1.9 | 3.9 | 4.7 | 3 % | 1 % | 1.01 | 0.98 | 2122 / 2123 |
| 145.0 | llama | 4565 | 3.7 | +2.1 | 4.0 | 4.8 | 3 % | 1 % | 1.01 | 0.98 | 2121 / 2123 |
| 147.5 | llama | 4565 | 3.8 | +2.3 | 4.1 | 4.8 | 3 % | 1 % | 1.01 | 0.99 | 2121 / 2123 |
| 150.0 | llama | 4558 | 3.8 | +2.3 | 4.1 | 4.7 | 3 % | 1 % | 1.01 | 0.98 | 2121 / 2123 |
