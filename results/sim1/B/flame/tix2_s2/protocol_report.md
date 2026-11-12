# Protocolo CFD: tix2_s2

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2_seeds/s2/08_fluent/resnet_film`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **31.7 K** (sesgo -28.0 K) |
| Deriva de ese error (100-150 ms) | +1.30 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 33.3 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 21.6 / 13.0 / 23.3 / 12.6 K |
| p95 abs dT, celdas calientes | 82 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 26 % / 24 %, ×1.14 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 10 %, ×1.14 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 12 %, ×0.93 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 129 % / 119 %, ×2.28 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.07 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 27 % |
| Error L1 del campo de calor liberado (celdas calientes) | 216 % |
| GA18 / OOD | 0.0 % / 14.2 % |
| Coste | 2.29 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 27089 (8455) | 0.179 | 26 % | 24 % | 14 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4517 | 23.3 | -22.2 | 9.9 | 17.9 | 21 % | 5 % | 1.00 | 1.06 | 2123 / 2089 |
| 105.0 | llama | 4534 | 27.6 | -24.8 | 14.8 | 23.8 | 23 % | 8 % | 1.00 | 1.09 | 2123 / 2088 |
| 107.5 | llama | 4538 | 29.4 | -26.4 | 16.6 | 25.0 | 23 % | 10 % | 1.00 | 1.12 | 2123 / 2088 |
| 110.0 | llama | 4538 | 30.5 | -27.5 | 17.4 | 25.8 | 23 % | 11 % | 0.99 | 1.14 | 2123 / 2088 |
| 112.5 | llama | 4538 | 31.2 | -28.2 | 18.3 | 26.6 | 24 % | 13 % | 0.99 | 1.14 | 2123 / 2088 |
| 115.0 | llama | 4542 | 31.6 | -28.6 | 19.2 | 27.2 | 24 % | 14 % | 0.99 | 1.14 | 2123 / 2088 |
| 117.5 | llama | 4543 | 32.0 | -28.8 | 20.1 | 27.7 | 24 % | 16 % | 0.99 | 1.14 | 2123 / 2087 |
| 120.0 | llama | 4546 | 32.1 | -29.2 | 20.9 | 28.3 | 25 % | 17 % | 0.99 | 1.08 | 2123 / 2087 |
| 122.5 | llama | 4546 | 32.7 | -29.4 | 22.5 | 29.3 | 26 % | 18 % | 0.99 | 1.09 | 2123 / 2087 |
| 125.0 | llama | 4562 | 32.9 | -29.1 | 23.5 | 30.2 | 27 % | 19 % | 0.99 | 1.07 | 2123 / 2087 |
| 127.5 | llama | 4570 | 32.9 | -29.0 | 24.1 | 31.1 | 27 % | 21 % | 0.99 | 1.06 | 2123 / 2088 |
| 130.0 | llama | 4576 | 33.0 | -28.8 | 25.0 | 32.3 | 28 % | 22 % | 0.99 | 1.06 | 2123 / 2088 |
| 132.5 | llama | 4578 | 33.1 | -28.7 | 25.2 | 33.3 | 28 % | 23 % | 0.99 | 1.06 | 2123 / 2088 |
| 135.0 | llama | 4574 | 33.1 | -28.7 | 25.3 | 34.2 | 28 % | 23 % | 0.99 | 1.06 | 2123 / 2088 |
| 137.5 | llama | 4564 | 32.5 | -28.8 | 24.1 | 34.3 | 28 % | 24 % | 0.99 | 1.05 | 2122 / 2087 |
| 140.0 | llama | 4571 | 32.9 | -28.5 | 24.5 | 35.0 | 29 % | 24 % | 0.99 | 1.03 | 2122 / 2087 |
| 142.5 | llama | 4570 | 33.1 | -28.3 | 24.8 | 35.3 | 29 % | 24 % | 0.99 | 1.03 | 2122 / 2088 |
| 145.0 | llama | 4569 | 33.4 | -28.3 | 25.2 | 35.8 | 29 % | 24 % | 0.99 | 1.02 | 2121 / 2089 |
| 147.5 | llama | 4566 | 33.5 | -28.5 | 25.4 | 36.6 | 30 % | 25 % | 0.99 | 1.02 | 2121 / 2089 |
| 150.0 | llama | 4557 | 33.8 | -28.9 | 25.9 | 37.5 | 31 % | 25 % | 0.99 | 1.02 | 2121 / 2088 |
