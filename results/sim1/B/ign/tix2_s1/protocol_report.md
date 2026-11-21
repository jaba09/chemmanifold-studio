# Protocolo CFD: tix2_s1

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2_seeds/s1/08_fluent/resnet_film`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.40 / -1.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +383 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +305 K |
| Media abs dT en la llama | 142.2 K |
| Media abs dT en la boquilla | 5.4 K |
| Media abs dT, celdas calientes | 0.9 K |
| Error L1 de OH, celdas calientes | 97 % |
| GA18 / OOD | 0.0 % / 6.2 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **545.5 K** (sesgo -191.6 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 28.3 / 330.4 / 0.8 / 446.3 K |
| p95 abs dT, celdas calientes | 66 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 53 % / 182 %, ×1.29 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 197 % / 165 %, ×2.44 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 148 % / 198 %, ×0.73 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 642 % / 505 %, ×6.83 |
| Volumen por encima de 1500 K, modelo/DI | ×0.82 |
| Punta / base de la llama en el eje, modelo - DI | +0.7 / +4.2 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×997.90 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 40517 % |
| Error L1 del campo de calor liberado (celdas calientes) | 131406 % |
| GA18 / OOD | 0.0 % / 2.9 % |
| Coste | 3.14 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 164.4 K, caliente 7.7 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 3310 (1680) | 0.186 | 14 % | 50 % | 3 % |
| llama | 861 (434) | 0.292 | 23 % | 46 % | 5 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 98 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.2 | 95 % | 104 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 67 | 241.7 | +241.7 | 0.8 | 4.7 | 104 % | 13936 % | – | 6484.46 | 1480 / 1750 |
| 2.0 | arranque | 137 | 305.4 | +305.4 | 1.6 | 9.6 | 109 % | 14942 % | – | 450.10 | 1480 / 1863 |
| 2.5 | arranque | 174 | 183.2 | +182.5 | 1.5 | 9.1 | 101 % | 716 % | 2.32 | 2.91 | 1820 / 1900 |
| 3.0 | arranque | 215 | 121.4 | +2.4 | 1.3 | 7.3 | 97 % | 213 % | 1.39 | 5.03 | 2056 / 1929 |
| 3.5 | arranque | 250 | 98.6 | -17.5 | 1.1 | 6.4 | 96 % | 134 % | 1.20 | 6.78 | 2073 / 1952 |
| 4.0 | arranque | 277 | 76.3 | -25.3 | 1.0 | 5.9 | 94 % | 104 % | 1.13 | 7.37 | 2088 / 1967 |
| 4.5 | arranque | 305 | 59.9 | -30.0 | 1.0 | 5.4 | 91 % | 91 % | 1.10 | 7.75 | 2094 / 1979 |
| 5.0 | arranque | 326 | 51.3 | -34.9 | 1.0 | 5.4 | 88 % | 84 % | 1.06 | 8.03 | 2098 / 1991 |
| 7.5 | transicion | 466 | 63.4 | -49.8 | 1.5 | 9.2 | 50 % | 79 % | 0.93 | 8.11 | 2112 / 2024 |
| 10.0 | transicion | 613 | 79.3 | -41.9 | 2.8 | 17.5 | 42 % | 119 % | 0.88 | 5.93 | 2119 / 2058 |
| 12.5 | transicion | 753 | 88.7 | -37.4 | 4.0 | 25.2 | 37 % | 130 % | 0.84 | 5.25 | 2124 / 2089 |
| 15.0 | transicion | 887 | 91.0 | -37.1 | 5.1 | 32.3 | 35 % | 135 % | 0.82 | 5.84 | 2127 / 2104 |
| 17.5 | transicion | 1041 | 124.5 | -47.5 | 7.0 | 44.6 | 35 % | 129 % | 0.81 | 5.81 | 2129 / 2108 |
| 20.0 | transicion | 1243 | 267.2 | -102.2 | 12.7 | 81.7 | 38 % | 135 % | 0.78 | 155.16 | 2131 / 2096 |
| 22.5 | transicion | 1517 | 436.5 | -158.0 | 20.6 | 133.0 | 45 % | 164 % | 0.80 | 748.73 | 2133 / 2093 |
| 25.0 | llama | 1831 | 545.5 | -191.6 | 28.3 | 183.0 | 53 % | 197 % | 0.82 | 997.90 | 2134 / 2088 |
