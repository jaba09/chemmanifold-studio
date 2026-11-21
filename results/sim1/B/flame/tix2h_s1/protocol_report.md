# Protocolo CFD: tix2h_s1

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2h_seeds/s1/08_fluent/resnet_film`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **26.3 K** (sesgo -12.5 K) |
| Deriva de ese error (100-150 ms) | +1.52 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 28.9 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 43.2 / 59.2 / 45.2 / 28.4 K |
| p95 abs dT, celdas calientes | 134 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 14 % / 11 %, ×1.03 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 75 % / 25 %, ×1.10 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 7 % / 10 %, ×1.05 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 53 % / 46 %, ×0.84 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.60 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 33 % |
| Error L1 del campo de calor liberado (celdas calientes) | 324 % |
| GA18 / OOD | 0.0 % / 26.4 % |
| Coste | 2.03 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 30982 (11594) | 0.282 | 32 % | 44 % | 26 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4735 | 20.1 | -2.3 | 13.9 | 17.2 | 12 % | 33 % | 1.02 | 3.60 | 2123 / 2112 |
| 105.0 | llama | 4759 | 23.7 | -4.6 | 20.5 | 22.4 | 12 % | 43 % | 1.02 | 3.62 | 2123 / 2109 |
| 107.5 | llama | 4692 | 22.5 | -9.7 | 25.4 | 25.3 | 12 % | 46 % | 1.01 | 3.62 | 2123 / 2108 |
| 110.0 | llama | 4723 | 24.5 | -11.4 | 31.2 | 27.2 | 13 % | 54 % | 1.01 | 3.64 | 2123 / 2106 |
| 112.5 | llama | 4740 | 25.3 | -12.1 | 35.8 | 29.2 | 14 % | 60 % | 1.00 | 3.65 | 2123 / 2106 |
| 115.0 | llama | 4660 | 24.9 | -14.9 | 39.7 | 30.6 | 15 % | 64 % | 1.00 | 3.63 | 2123 / 2106 |
| 117.5 | llama | 4670 | 25.7 | -15.0 | 42.8 | 31.6 | 14 % | 68 % | 0.99 | 3.63 | 2123 / 2105 |
| 120.0 | llama | 4680 | 25.9 | -15.7 | 44.3 | 32.5 | 14 % | 72 % | 0.99 | 3.63 | 2123 / 2105 |
| 122.5 | llama | 4691 | 26.8 | -14.7 | 45.8 | 32.4 | 14 % | 76 % | 1.00 | 3.61 | 2123 / 2105 |
| 125.0 | llama | 4691 | 26.6 | -14.9 | 46.9 | 32.7 | 14 % | 78 % | 0.99 | 3.62 | 2123 / 2105 |
| 127.5 | llama | 4701 | 26.1 | -16.1 | 47.8 | 32.1 | 14 % | 81 % | 1.00 | 3.62 | 2123 / 2105 |
| 130.0 | llama | 4707 | 27.6 | -14.4 | 48.6 | 31.6 | 14 % | 84 % | 1.00 | 3.60 | 2123 / 2105 |
| 132.5 | llama | 4748 | 27.1 | -14.3 | 48.7 | 31.5 | 14 % | 84 % | 1.00 | 3.60 | 2123 / 2105 |
| 135.0 | llama | 4720 | 26.9 | -14.3 | 48.9 | 30.4 | 14 % | 86 % | 1.00 | 3.58 | 2123 / 2105 |
| 137.5 | llama | 4715 | 27.6 | -13.8 | 51.1 | 30.4 | 15 % | 92 % | 1.00 | 3.56 | 2122 / 2104 |
| 140.0 | llama | 4727 | 26.7 | -15.2 | 53.4 | 29.8 | 15 % | 92 % | 1.00 | 3.55 | 2122 / 2104 |
| 142.5 | llama | 4790 | 28.5 | -12.8 | 55.5 | 28.8 | 14 % | 95 % | 1.00 | 3.56 | 2122 / 2103 |
| 145.0 | llama | 4859 | 30.0 | -11.0 | 55.8 | 28.5 | 15 % | 97 % | 1.00 | 3.57 | 2121 / 2104 |
| 147.5 | llama | 4846 | 30.0 | -10.9 | 54.6 | 27.4 | 14 % | 98 % | 1.00 | 3.53 | 2121 / 2104 |
| 150.0 | llama | 4784 | 29.4 | -12.5 | 53.0 | 27.4 | 14 % | 99 % | 1.00 | 3.54 | 2121 / 2104 |
