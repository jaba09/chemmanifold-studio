# Protocolo CFD: ood8_s0

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/ood8_s0`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **38.6 K** (sesgo -10.5 K) |
| Deriva de ese error (100-150 ms) | +15.23 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 66.5 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 50.4 / 44.0 / 46.5 / 196.4 K |
| p95 abs dT, celdas calientes | 172 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 36 % / 26 %, ×1.15 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 26 % / 17 %, ×1.16 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 19 % / 27 %, ×0.82 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 51 % / 40 %, ×1.15 |
| Volumen por encima de 1500 K, modelo/DI | ×0.96 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×2.16 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / -543 % |
| Error L1 del campo de calor liberado (celdas calientes) | 708 % |
| GA18 / OOD | 0.0 % / 46.8 % |
| Coste | 2.30 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 28489 (12479) | 0.206 | 25 % | 36 % | 23 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4518 | 10.5 | -2.1 | 5.3 | 9.2 | 10 % | 5 % | 1.00 | 2.25 | 2123 / 2129 |
| 105.0 | llama | 4521 | 10.9 | -4.7 | 7.7 | 11.1 | 20 % | 8 % | 0.99 | 2.29 | 2123 / 2127 |
| 107.5 | llama | 4518 | 10.8 | -5.9 | 8.5 | 11.4 | 21 % | 11 % | 0.99 | 2.29 | 2123 / 2127 |
| 110.0 | llama | 4518 | 10.4 | -6.6 | 9.6 | 12.6 | 23 % | 13 % | 0.99 | 2.29 | 2123 / 2128 |
| 112.5 | llama | 4529 | 10.3 | -6.5 | 17.5 | 25.1 | 24 % | 15 % | 0.99 | 2.28 | 2123 / 2128 |
| 115.0 | llama | 4564 | 13.3 | -5.8 | 26.7 | 37.5 | 26 % | 18 % | 0.98 | 2.26 | 2123 / 2128 |
| 117.5 | llama | 4570 | 18.5 | -5.7 | 34.8 | 53.2 | 29 % | 22 % | 0.98 | 2.24 | 2123 / 2128 |
| 120.0 | llama | 4617 | 26.8 | -6.6 | 43.0 | 73.8 | 31 % | 27 % | 0.98 | 2.22 | 2123 / 2130 |
| 122.5 | llama | 4641 | 34.4 | -6.3 | 53.8 | 99.6 | 34 % | 31 % | 0.97 | 2.20 | 2123 / 2132 |
| 125.0 | llama | 4660 | 38.9 | -6.7 | 58.1 | 109.4 | 36 % | 33 % | 0.96 | 2.17 | 2123 / 2133 |
| 127.5 | llama | 4664 | 43.2 | -7.3 | 61.5 | 119.7 | 38 % | 34 % | 0.96 | 2.13 | 2123 / 2133 |
| 130.0 | llama | 4672 | 47.6 | -8.4 | 64.9 | 129.9 | 41 % | 34 % | 0.95 | 2.10 | 2123 / 2132 |
| 132.5 | llama | 4673 | 51.5 | -10.0 | 67.4 | 138.7 | 43 % | 34 % | 0.95 | 2.08 | 2123 / 2131 |
| 135.0 | llama | 4672 | 54.9 | -11.9 | 69.7 | 146.0 | 45 % | 33 % | 0.95 | 2.06 | 2123 / 2130 |
| 137.5 | llama | 4667 | 58.1 | -14.1 | 71.9 | 152.5 | 47 % | 33 % | 0.94 | 2.05 | 2122 / 2129 |
| 140.0 | llama | 4664 | 61.4 | -16.3 | 74.8 | 158.7 | 49 % | 33 % | 0.94 | 2.05 | 2122 / 2127 |
| 142.5 | llama | 4660 | 64.5 | -18.4 | 78.4 | 163.8 | 51 % | 33 % | 0.93 | 2.05 | 2122 / 2125 |
| 145.0 | llama | 4649 | 67.0 | -20.2 | 81.8 | 167.4 | 52 % | 34 % | 0.93 | 2.05 | 2121 / 2123 |
| 147.5 | llama | 4645 | 69.0 | -21.9 | 85.1 | 170.1 | 54 % | 34 % | 0.92 | 2.05 | 2121 / 2122 |
| 150.0 | llama | 4633 | 70.7 | -23.6 | 88.6 | 171.3 | 55 % | 35 % | 0.92 | 2.04 | 2121 / 2121 |
