# Protocolo CFD: tix2h_s0

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2h/08_fluent/resnet_film`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **11.8 K** (sesgo -2.8 K) |
| Deriva de ese error (100-150 ms) | +0.33 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 12.6 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 21.8 / 22.1 / 35.3 / 6.1 K |
| p95 abs dT, celdas calientes | 103 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 32 % / 33 %, ×1.28 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 66 % / 5 %, ×1.54 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 6 %, ×0.98 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 31 % / 30 %, ×0.80 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×7.50 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 10 % |
| Error L1 del campo de calor liberado (celdas calientes) | 604 % |
| GA18 / OOD | 0.0 % / 4.6 % |
| Coste | 1.99 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 25728 (3221) | 0.0752 | 12 % | 6 % | 17 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4523 | 10.3 | -2.6 | 5.2 | 9.0 | 31 % | 4 % | 1.00 | 7.61 | 2123 / 2124 |
| 105.0 | llama | 4533 | 11.7 | -2.3 | 7.2 | 11.5 | 32 % | 7 % | 1.00 | 7.60 | 2123 / 2125 |
| 107.5 | llama | 4539 | 12.1 | -2.1 | 9.3 | 12.3 | 32 % | 14 % | 1.00 | 7.59 | 2123 / 2125 |
| 110.0 | llama | 4540 | 11.9 | -2.2 | 12.8 | 11.7 | 32 % | 27 % | 1.00 | 7.59 | 2123 / 2126 |
| 112.5 | llama | 4540 | 11.6 | -2.4 | 17.5 | 11.0 | 32 % | 43 % | 1.00 | 7.59 | 2123 / 2126 |
| 115.0 | llama | 4541 | 11.3 | -2.6 | 21.6 | 10.6 | 32 % | 57 % | 1.00 | 7.59 | 2123 / 2126 |
| 117.5 | llama | 4536 | 11.1 | -2.9 | 24.2 | 10.5 | 32 % | 67 % | 1.00 | 7.58 | 2123 / 2127 |
| 120.0 | llama | 4542 | 11.0 | -3.0 | 25.3 | 10.6 | 32 % | 73 % | 1.00 | 7.57 | 2123 / 2127 |
| 122.5 | llama | 4543 | 11.1 | -3.1 | 25.7 | 10.8 | 32 % | 77 % | 1.00 | 7.56 | 2123 / 2127 |
| 125.0 | llama | 4550 | 11.3 | -3.1 | 25.5 | 11.2 | 33 % | 79 % | 0.99 | 7.55 | 2123 / 2127 |
| 127.5 | llama | 4554 | 11.5 | -3.1 | 25.4 | 11.8 | 33 % | 81 % | 0.99 | 7.54 | 2123 / 2127 |
| 130.0 | llama | 4559 | 11.6 | -3.0 | 25.6 | 12.7 | 32 % | 83 % | 0.99 | 7.52 | 2123 / 2127 |
| 132.5 | llama | 4562 | 11.8 | -3.0 | 25.8 | 13.6 | 32 % | 85 % | 0.99 | 7.50 | 2123 / 2127 |
| 135.0 | llama | 4565 | 12.0 | -3.0 | 26.1 | 14.5 | 32 % | 87 % | 0.99 | 7.47 | 2123 / 2126 |
| 137.5 | llama | 4567 | 12.1 | -3.0 | 26.2 | 15.5 | 32 % | 88 % | 0.99 | 7.43 | 2122 / 2126 |
| 140.0 | llama | 4569 | 12.2 | -2.9 | 26.2 | 16.3 | 32 % | 89 % | 0.99 | 7.39 | 2122 / 2125 |
| 142.5 | llama | 4568 | 12.3 | -2.8 | 26.2 | 17.0 | 32 % | 90 % | 0.99 | 7.36 | 2122 / 2125 |
| 145.0 | llama | 4564 | 12.5 | -2.7 | 26.3 | 17.7 | 31 % | 90 % | 0.99 | 7.33 | 2121 / 2125 |
| 147.5 | llama | 4564 | 12.8 | -2.7 | 26.6 | 18.2 | 31 % | 91 % | 0.99 | 7.33 | 2121 / 2124 |
| 150.0 | llama | 4559 | 13.1 | -2.8 | 27.0 | 18.6 | 31 % | 92 % | 0.99 | 7.33 | 2121 / 2124 |
