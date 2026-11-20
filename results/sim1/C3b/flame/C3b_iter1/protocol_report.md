# Protocolo CFD: C3b_iter1

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2b/iter1/ensemble`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **34.3 K** (sesgo -1.1 K) |
| Deriva de ese error (100-150 ms) | +25.55 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 97.7 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 48.8 / 49.9 / 46.7 / 146.5 K |
| p95 abs dT, celdas calientes | 179 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 17 % / 17 %, ×1.01 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 19 % / 10 %, ×1.07 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 21 %, ×0.85 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 27 % / 26 %, ×1.06 |
| Volumen por encima de 1500 K, modelo/DI | ×0.98 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.89 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 10 % |
| Error L1 del campo de calor liberado (celdas calientes) | 51 % |
| GA18 / OOD | 0.0 % / 5.3 % |
| Coste | 3.41 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 24295 (2849) | 0.0278 | 4 % | 2 % | 2 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4508 | 1.7 | -0.3 | 1.4 | 1.3 | 3 % | 1 % | 1.00 | 0.91 | 2123 / 2121 |
| 105.0 | llama | 4514 | 1.9 | -0.3 | 1.9 | 1.6 | 3 % | 2 % | 1.00 | 0.91 | 2123 / 2121 |
| 107.5 | llama | 4513 | 2.0 | -0.4 | 2.4 | 1.9 | 3 % | 3 % | 1.00 | 0.91 | 2123 / 2121 |
| 110.0 | llama | 4516 | 2.1 | -0.5 | 2.8 | 2.1 | 3 % | 4 % | 1.00 | 0.91 | 2123 / 2122 |
| 112.5 | llama | 4517 | 2.1 | -0.7 | 3.2 | 2.3 | 3 % | 5 % | 1.00 | 0.91 | 2123 / 2122 |
| 115.0 | llama | 4521 | 2.2 | -0.9 | 3.8 | 2.4 | 3 % | 6 % | 1.00 | 0.91 | 2123 / 2122 |
| 117.5 | llama | 4519 | 2.2 | -1.0 | 4.1 | 2.5 | 3 % | 7 % | 1.00 | 0.91 | 2123 / 2122 |
| 120.0 | llama | 4526 | 2.2 | -1.0 | 4.3 | 2.6 | 3 % | 7 % | 1.00 | 0.91 | 2123 / 2122 |
| 122.5 | llama | 4525 | 2.2 | -1.0 | 4.8 | 2.8 | 3 % | 7 % | 1.00 | 0.91 | 2123 / 2122 |
| 125.0 | llama | 4544 | 3.1 | -0.8 | 7.8 | 6.5 | 3 % | 8 % | 1.00 | 0.91 | 2123 / 2122 |
| 127.5 | llama | 4605 | 11.2 | +1.0 | 19.2 | 35.3 | 6 % | 10 % | 1.00 | 0.91 | 2123 / 2122 |
| 130.0 | llama | 4637 | 21.8 | +2.8 | 33.7 | 69.9 | 10 % | 14 % | 0.99 | 0.90 | 2123 / 2122 |
| 132.5 | llama | 4680 | 34.2 | +4.0 | 51.2 | 110.9 | 16 % | 18 % | 0.98 | 0.89 | 2123 / 2122 |
| 135.0 | llama | 4717 | 47.5 | +4.3 | 69.6 | 154.9 | 22 % | 24 % | 0.98 | 0.89 | 2123 / 2121 |
| 137.5 | llama | 4728 | 60.8 | +3.5 | 87.0 | 188.3 | 28 % | 29 % | 0.96 | 0.88 | 2122 / 2121 |
| 140.0 | llama | 4747 | 73.7 | +2.0 | 103.9 | 209.9 | 35 % | 35 % | 0.95 | 0.86 | 2122 / 2121 |
| 142.5 | llama | 4736 | 86.0 | -1.0 | 119.8 | 227.5 | 41 % | 41 % | 0.94 | 0.86 | 2122 / 2120 |
| 145.0 | llama | 4700 | 97.7 | -5.2 | 135.4 | 241.7 | 47 % | 46 % | 0.92 | 0.86 | 2121 / 2123 |
| 147.5 | llama | 4683 | 109.5 | -10.5 | 151.3 | 254.4 | 53 % | 52 % | 0.91 | 0.85 | 2121 / 2129 |
| 150.0 | llama | 4680 | 121.6 | -16.4 | 167.9 | 266.0 | 58 % | 57 % | 0.89 | 0.85 | 2121 / 2135 |
