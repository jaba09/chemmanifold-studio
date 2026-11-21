# Protocolo CFD: C3_iter1

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2/iter1/ensemble`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **11.1 K** (sesgo -8.9 K) |
| Deriva de ese error (100-150 ms) | +1.34 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 13.0 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 39.2 / 43.1 / 66.0 / 37.3 K |
| p95 abs dT, celdas calientes | 194 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 8 % / 7 %, ×1.05 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 3 %, ×0.98 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 2 % / 2 %, ×1.02 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 14 % / 14 %, ×1.13 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.30 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 11 % |
| Error L1 del campo de calor liberado (celdas calientes) | 33 % |
| GA18 / OOD | 0.0 % / 4.2 % |
| Coste | 3.85 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 23770 (2227) | 0.0399 | 6 % | 2 % | 8 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4505 | 6.1 | -5.7 | 2.8 | 4.1 | 7 % | 3 % | 1.00 | 1.30 | 2123 / 2105 |
| 105.0 | llama | 4512 | 6.6 | -6.3 | 3.9 | 5.8 | 7 % | 4 % | 1.00 | 1.30 | 2123 / 2104 |
| 107.5 | llama | 4511 | 7.1 | -6.7 | 5.2 | 8.2 | 7 % | 5 % | 1.00 | 1.30 | 2123 / 2104 |
| 110.0 | llama | 4514 | 7.9 | -7.4 | 9.8 | 10.3 | 7 % | 6 % | 1.00 | 1.30 | 2123 / 2103 |
| 112.5 | llama | 4523 | 9.2 | -8.2 | 17.8 | 12.7 | 7 % | 6 % | 1.00 | 1.31 | 2123 / 2103 |
| 115.0 | llama | 4529 | 10.6 | -9.1 | 27.7 | 15.4 | 7 % | 7 % | 1.00 | 1.31 | 2123 / 2103 |
| 117.5 | llama | 4532 | 12.0 | -10.0 | 38.3 | 18.2 | 7 % | 7 % | 0.99 | 1.31 | 2123 / 2102 |
| 120.0 | llama | 4539 | 12.9 | -10.7 | 47.2 | 20.2 | 8 % | 7 % | 0.99 | 1.32 | 2123 / 2102 |
| 122.5 | llama | 4532 | 12.9 | -11.0 | 51.0 | 20.3 | 8 % | 8 % | 0.99 | 1.31 | 2123 / 2102 |
| 125.0 | llama | 4548 | 12.4 | -10.9 | 51.4 | 19.8 | 8 % | 8 % | 0.98 | 1.31 | 2123 / 2102 |
| 127.5 | llama | 4550 | 12.0 | -10.6 | 51.2 | 19.5 | 8 % | 9 % | 0.98 | 1.31 | 2123 / 2102 |
| 130.0 | llama | 4560 | 11.7 | -10.2 | 50.8 | 19.6 | 8 % | 10 % | 0.98 | 1.30 | 2123 / 2102 |
| 132.5 | llama | 4565 | 11.7 | -9.8 | 50.8 | 20.0 | 8 % | 10 % | 0.98 | 1.30 | 2123 / 2102 |
| 135.0 | llama | 4572 | 11.9 | -9.5 | 51.2 | 20.6 | 8 % | 11 % | 0.98 | 1.30 | 2123 / 2102 |
| 137.5 | llama | 4577 | 12.2 | -9.2 | 52.0 | 21.2 | 8 % | 11 % | 0.98 | 1.30 | 2122 / 2102 |
| 140.0 | llama | 4581 | 12.4 | -8.9 | 52.6 | 21.9 | 8 % | 11 % | 0.98 | 1.30 | 2122 / 2102 |
| 142.5 | llama | 4582 | 12.7 | -8.6 | 53.4 | 22.5 | 8 % | 11 % | 0.98 | 1.30 | 2122 / 2101 |
| 145.0 | llama | 4584 | 13.0 | -8.4 | 54.4 | 22.9 | 9 % | 12 % | 0.98 | 1.30 | 2121 / 2101 |
| 147.5 | llama | 4585 | 13.3 | -8.4 | 55.8 | 23.3 | 9 % | 12 % | 0.98 | 1.29 | 2121 / 2101 |
| 150.0 | llama | 4581 | 13.5 | -8.4 | 57.3 | 23.7 | 9 % | 13 % | 0.98 | 1.29 | 2121 / 2100 |
