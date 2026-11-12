# Protocolo CFD: ood8_s1

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/ood8_s1`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **70.7 K** (sesgo -36.4 K) |
| Deriva de ese error (100-150 ms) | +10.75 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 82.4 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 84.1 / 82.9 / 76.1 / 222.9 K |
| p95 abs dT, celdas calientes | 342 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 55 % / 51 %, ×1.21 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 45 % / 34 %, ×0.56 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 25 % / 40 %, ×0.86 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 199 % / 168 %, ×2.59 |
| Volumen por encima de 1500 K, modelo/DI | ×0.94 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×-12.87 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / -7156 % |
| Error L1 del campo de calor liberado (celdas calientes) | 9729 % |
| GA18 / OOD | 0.0 % / 60.6 % |
| Coste | 1.83 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 29009 (15742) | 0.257 | 25 % | 46 % | 32 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4524 | 12.5 | -9.2 | 10.8 | 24.9 | 20 % | 5 % | 1.00 | 1.90 | 2123 / 2106 |
| 105.0 | llama | 4588 | 33.3 | -9.7 | 38.7 | 107.6 | 30 % | 12 % | 0.99 | -4.87 | 2123 / 2105 |
| 107.5 | llama | 4550 | 44.8 | -19.2 | 64.6 | 121.9 | 39 % | 22 % | 0.96 | -17.28 | 2123 / 2110 |
| 110.0 | llama | 4566 | 55.6 | -20.6 | 81.2 | 140.5 | 46 % | 40 % | 0.94 | -14.77 | 2123 / 2140 |
| 112.5 | llama | 4611 | 62.6 | -22.0 | 81.9 | 152.6 | 51 % | 48 % | 0.95 | -13.59 | 2123 / 2150 |
| 115.0 | llama | 4614 | 68.2 | -26.8 | 86.1 | 161.5 | 56 % | 50 % | 0.95 | -13.95 | 2123 / 2145 |
| 117.5 | llama | 4586 | 71.3 | -30.5 | 88.4 | 166.6 | 59 % | 50 % | 0.95 | -14.15 | 2123 / 2142 |
| 120.0 | llama | 4592 | 75.0 | -33.7 | 90.8 | 173.2 | 62 % | 51 % | 0.94 | -14.24 | 2123 / 2141 |
| 122.5 | llama | 4609 | 79.2 | -36.8 | 94.4 | 177.8 | 63 % | 52 % | 0.94 | -14.61 | 2123 / 2140 |
| 125.0 | llama | 4629 | 81.9 | -40.6 | 96.2 | 176.6 | 64 % | 52 % | 0.94 | -14.73 | 2123 / 2139 |
| 127.5 | llama | 4629 | 83.3 | -43.6 | 97.3 | 175.1 | 64 % | 52 % | 0.93 | -14.33 | 2123 / 2137 |
| 130.0 | llama | 4620 | 83.3 | -46.4 | 97.1 | 170.7 | 63 % | 52 % | 0.93 | -13.76 | 2123 / 2135 |
| 132.5 | llama | 4608 | 83.8 | -47.9 | 98.2 | 169.6 | 63 % | 52 % | 0.93 | -13.12 | 2123 / 2131 |
| 135.0 | llama | 4595 | 83.9 | -48.7 | 98.3 | 167.8 | 62 % | 52 % | 0.93 | -12.77 | 2123 / 2129 |
| 137.5 | llama | 4585 | 83.5 | -48.9 | 97.5 | 167.8 | 62 % | 52 % | 0.93 | -12.89 | 2122 / 2129 |
| 140.0 | llama | 4598 | 83.1 | -49.0 | 96.3 | 168.6 | 61 % | 52 % | 0.93 | -13.70 | 2122 / 2130 |
| 142.5 | llama | 4587 | 82.7 | -49.0 | 94.2 | 167.5 | 61 % | 51 % | 0.93 | -13.97 | 2122 / 2132 |
| 145.0 | llama | 4570 | 82.4 | -48.7 | 91.7 | 166.3 | 60 % | 51 % | 0.92 | -14.11 | 2121 / 2134 |
| 147.5 | llama | 4567 | 82.4 | -48.8 | 90.0 | 164.6 | 60 % | 52 % | 0.91 | -14.24 | 2121 / 2135 |
| 150.0 | llama | 4566 | 81.7 | -48.6 | 87.7 | 162.0 | 59 % | 52 % | 0.91 | -14.25 | 2121 / 2135 |
