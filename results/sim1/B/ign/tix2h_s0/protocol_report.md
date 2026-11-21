# Protocolo CFD: tix2h_s0

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2h/08_fluent/resnet_film`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 3.00 / +0.60 ms |
| Máximo exceso de Tmax del dominio sobre DI | +6 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -261 K |
| Media abs dT en la llama | 110.4 K |
| Media abs dT en la boquilla | 2.2 K |
| Media abs dT, celdas calientes | 0.5 K |
| Error L1 de OH, celdas calientes | 51 % |
| GA18 / OOD | 0.0 % / 0.3 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **12.1 K** (sesgo +2.8 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.9 / 5.0 / 0.4 / 6.3 K |
| p95 abs dT, celdas calientes | 4 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 212 % / 26 %, ×2.82 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 49 % / 4 %, ×1.40 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 10 % / 4 %, ×1.08 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 91 % / 34 %, ×1.32 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×7.86 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 117 % |
| Error L1 del campo de calor liberado (celdas calientes) | 756 % |
| GA18 / OOD | 0.0 % / 23.6 % |
| Coste | 3.14 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 14.5 K, caliente 0.6 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4658 (343) | 0.0409 | 8 % | 1 % | 7 % |
| llama | 873 (44) | 0.0247 | 4 % | 2 % | 9 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 99 % | 100 % | – | – | 1480 / 1481 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.3 | 94 % | 100 % | – | – | 1480 / 1485 |
| 1.5 | arranque | 0 | – | – | 0.2 | 0.5 | 79 % | 99 % | – | – | 1480 / 1486 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.6 | 58 % | 95 % | – | – | 1480 / 1486 |
| 2.5 | arranque | 63 | 250.2 | -250.2 | 0.6 | 3.5 | 39 % | 98 % | 0.00 | 0.00 | 1820 / 1486 |
| 3.0 | arranque | 161 | 260.7 | -260.7 | 1.4 | 8.1 | 24 % | 64 % | 0.56 | 4.46 | 2056 / 1722 |
| 3.5 | arranque | 210 | 72.4 | -72.4 | 0.6 | 3.2 | 19 % | 43 % | 0.94 | 2.58 | 2073 / 1912 |
| 4.0 | arranque | 253 | 32.6 | -27.9 | 0.4 | 1.9 | 21 % | 37 % | 1.00 | 4.50 | 2088 / 2003 |
| 4.5 | arranque | 290 | 24.8 | -16.4 | 0.4 | 1.7 | 31 % | 28 % | 1.02 | 5.20 | 2094 / 2035 |
| 5.0 | arranque | 320 | 21.7 | -11.5 | 0.4 | 1.8 | 48 % | 21 % | 1.01 | 5.71 | 2098 / 2051 |
| 7.5 | transicion | 463 | 16.9 | -3.3 | 0.5 | 1.8 | 82 % | 7 % | 1.00 | 6.61 | 2112 / 2081 |
| 10.0 | transicion | 600 | 15.5 | -0.2 | 0.5 | 1.9 | 80 % | 6 % | 1.01 | 7.16 | 2119 / 2098 |
| 12.5 | transicion | 738 | 14.9 | +1.1 | 0.6 | 2.2 | 93 % | 11 % | 1.01 | 7.44 | 2124 / 2108 |
| 15.0 | transicion | 862 | 14.4 | +2.3 | 0.6 | 2.5 | 115 % | 18 % | 1.01 | 7.63 | 2127 / 2115 |
| 17.5 | transicion | 995 | 13.8 | +2.6 | 0.7 | 2.7 | 204 % | 31 % | 1.01 | 7.77 | 2129 / 2122 |
| 20.0 | transicion | 1116 | 13.3 | +3.1 | 0.8 | 3.0 | 222 % | 40 % | 1.01 | 7.83 | 2131 / 2126 |
| 22.5 | transicion | 1245 | 12.7 | +3.0 | 0.8 | 3.2 | 229 % | 46 % | 1.01 | 7.87 | 2133 / 2130 |
| 25.0 | llama | 1369 | 12.1 | +2.8 | 0.9 | 3.4 | 212 % | 49 % | 1.01 | 7.86 | 2134 / 2133 |
