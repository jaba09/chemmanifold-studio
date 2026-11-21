# Protocolo CFD: C3_iter2

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2/iter2/ensemble`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **10.7 K** (sesgo -7.5 K) |
| Deriva de ese error (100-150 ms) | +1.78 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 13.6 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 42.1 / 48.2 / 70.6 / 35.3 K |
| p95 abs dT, celdas calientes | 189 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 8 % / 6 %, ×1.05 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 11 % / 3 %, ×1.01 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 4 % / 3 %, ×1.04 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 12 % / 11 %, ×1.11 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.27 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 12 % |
| Error L1 del campo de calor liberado (celdas calientes) | 32 % |
| GA18 / OOD | 0.0 % / 5.6 % |
| Coste | 3.65 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 23475 (2231) | 0.0506 | 7 % | 1 % | 9 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4507 | 5.0 | -4.7 | 2.5 | 3.8 | 6 % | 3 % | 1.00 | 1.27 | 2123 / 2106 |
| 105.0 | llama | 4512 | 5.6 | -5.2 | 3.4 | 5.6 | 6 % | 4 % | 1.00 | 1.27 | 2123 / 2105 |
| 107.5 | llama | 4514 | 6.1 | -5.7 | 5.3 | 8.1 | 6 % | 5 % | 1.00 | 1.27 | 2123 / 2105 |
| 110.0 | llama | 4519 | 7.0 | -6.3 | 10.4 | 10.3 | 6 % | 5 % | 1.00 | 1.27 | 2123 / 2105 |
| 112.5 | llama | 4528 | 8.2 | -7.1 | 17.9 | 12.2 | 6 % | 6 % | 1.00 | 1.27 | 2123 / 2104 |
| 115.0 | llama | 4540 | 9.5 | -7.8 | 27.7 | 15.5 | 6 % | 7 % | 1.00 | 1.27 | 2123 / 2104 |
| 117.5 | llama | 4557 | 10.7 | -8.4 | 37.4 | 18.7 | 7 % | 8 % | 1.00 | 1.27 | 2123 / 2104 |
| 120.0 | llama | 4582 | 11.5 | -8.9 | 45.1 | 20.9 | 7 % | 9 % | 1.00 | 1.28 | 2123 / 2103 |
| 122.5 | llama | 4581 | 11.9 | -9.2 | 50.9 | 22.2 | 7 % | 10 % | 0.99 | 1.28 | 2123 / 2103 |
| 125.0 | llama | 4590 | 12.3 | -9.5 | 57.4 | 23.6 | 9 % | 10 % | 0.99 | 1.28 | 2123 / 2103 |
| 127.5 | llama | 4587 | 12.5 | -9.7 | 61.7 | 24.1 | 10 % | 11 % | 0.99 | 1.28 | 2123 / 2103 |
| 130.0 | llama | 4588 | 11.8 | -9.3 | 60.7 | 23.1 | 9 % | 12 % | 0.99 | 1.28 | 2123 / 2103 |
| 132.5 | llama | 4585 | 11.4 | -8.7 | 58.6 | 22.9 | 9 % | 13 % | 0.99 | 1.27 | 2123 / 2103 |
| 135.0 | llama | 4590 | 11.5 | -8.1 | 56.8 | 23.3 | 9 % | 14 % | 0.99 | 1.27 | 2123 / 2103 |
| 137.5 | llama | 4598 | 11.9 | -7.5 | 55.7 | 24.1 | 9 % | 15 % | 0.99 | 1.26 | 2122 / 2103 |
| 140.0 | llama | 4600 | 12.5 | -7.1 | 55.5 | 25.0 | 10 % | 15 % | 0.99 | 1.26 | 2122 / 2103 |
| 142.5 | llama | 4603 | 13.0 | -6.8 | 56.2 | 25.7 | 10 % | 16 % | 0.99 | 1.26 | 2122 / 2103 |
| 145.0 | llama | 4602 | 13.5 | -6.6 | 57.7 | 26.1 | 10 % | 16 % | 0.99 | 1.26 | 2121 / 2102 |
| 147.5 | llama | 4600 | 14.1 | -6.6 | 59.7 | 26.5 | 10 % | 17 % | 0.98 | 1.26 | 2121 / 2102 |
| 150.0 | llama | 4600 | 14.7 | -6.6 | 61.5 | 27.6 | 11 % | 18 % | 0.98 | 1.26 | 2121 / 2102 |
