# Protocolo CFD: C3b_iter2

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2b/iter2/ensemble`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **84.0 K** (sesgo +9.1 K) |
| Deriva de ese error (100-150 ms) | +65.09 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 246.2 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 62.3 / 33.6 / 49.2 / 127.9 K |
| p95 abs dT, celdas calientes | 217 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 33 % / 33 %, ×0.99 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 18 % / 19 %, ×1.04 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 23 % / 34 %, ×0.94 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 40 % / 40 %, ×1.02 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.93 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 1046 % |
| Error L1 del campo de calor liberado (celdas calientes) | 1009 % |
| GA18 / OOD | 0.0 % / 5.8 % |
| Coste | 3.33 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 26064 (2564) | 0.0331 | 5 % | 3 % | 3 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4523 | 2.1 | +0.4 | 1.8 | 2.2 | 2 % | 2 % | 1.00 | 0.90 | 2123 / 2116 |
| 105.0 | llama | 4535 | 2.5 | +0.6 | 2.5 | 2.7 | 2 % | 3 % | 1.00 | 0.89 | 2123 / 2115 |
| 107.5 | llama | 4540 | 2.7 | +0.6 | 3.0 | 3.0 | 3 % | 4 % | 1.00 | 0.89 | 2123 / 2115 |
| 110.0 | llama | 4545 | 3.1 | +0.4 | 3.7 | 3.6 | 3 % | 4 % | 1.00 | 0.89 | 2123 / 2115 |
| 112.5 | llama | 4552 | 3.3 | +0.3 | 4.5 | 4.5 | 3 % | 4 % | 1.00 | 0.89 | 2123 / 2115 |
| 115.0 | llama | 4545 | 3.3 | +0.0 | 5.3 | 5.5 | 3 % | 5 % | 1.00 | 0.89 | 2123 / 2115 |
| 117.5 | llama | 4541 | 3.4 | -0.2 | 6.0 | 6.4 | 3 % | 5 % | 1.00 | 0.89 | 2123 / 2115 |
| 120.0 | llama | 4538 | 3.7 | -0.6 | 6.9 | 7.5 | 4 % | 6 % | 1.00 | 0.89 | 2123 / 2115 |
| 122.5 | llama | 4529 | 4.2 | -0.9 | 8.0 | 9.3 | 4 % | 7 % | 0.99 | 0.89 | 2123 / 2116 |
| 125.0 | llama | 4541 | 4.7 | -1.2 | 9.0 | 11.3 | 4 % | 7 % | 0.99 | 0.89 | 2123 / 2116 |
| 127.5 | llama | 4558 | 7.7 | -0.7 | 14.3 | 28.3 | 5 % | 9 % | 0.99 | 0.89 | 2123 / 2116 |
| 130.0 | llama | 4621 | 17.6 | +0.7 | 27.2 | 66.7 | 8 % | 10 % | 0.99 | 0.89 | 2123 / 2116 |
| 132.5 | llama | 4817 | 65.9 | +5.2 | 58.6 | 123.7 | 22 % | 15 % | 0.99 | 0.90 | 2123 / 2116 |
| 135.0 | llama | 5111 | 137.1 | +3.9 | 99.0 | 187.4 | 42 % | 22 % | 0.98 | 0.91 | 2123 / 2120 |
| 137.5 | llama | 5420 | 188.1 | +6.9 | 125.7 | 227.4 | 62 % | 30 % | 0.98 | 0.91 | 2122 / 2129 |
| 140.0 | llama | 5738 | 207.0 | +12.8 | 138.8 | 261.8 | 78 % | 35 % | 0.99 | 0.91 | 2122 / 2132 |
| 142.5 | llama | 5806 | 224.8 | +14.6 | 157.9 | 282.2 | 90 % | 40 % | 1.00 | 1.01 | 2122 / 2132 |
| 145.0 | llama | 5893 | 241.9 | +27.1 | 174.7 | 313.9 | 98 % | 45 % | 1.02 | 1.09 | 2121 / 2137 |
| 147.5 | llama | 6055 | 263.0 | +45.1 | 190.8 | 366.3 | 104 % | 52 % | 1.04 | 1.12 | 2121 / 2144 |
| 150.0 | llama | 6320 | 294.2 | +67.0 | 208.6 | 370.2 | 112 % | 57 % | 1.07 | 1.07 | 2121 / 2145 |
