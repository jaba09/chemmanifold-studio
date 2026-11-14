# Protocolo CFD: tix2h_s1

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2h_seeds/s1/08_fluent/resnet_film`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.80 / -0.60 ms |
| Máximo exceso de Tmax del dominio sobre DI | +427 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +334 K |
| Media abs dT en la llama | 109.4 K |
| Media abs dT en la boquilla | 3.2 K |
| Media abs dT, celdas calientes | 0.6 K |
| Error L1 de OH, celdas calientes | 99 % |
| GA18 / OOD | 0.0 % / 0.2 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **15.9 K** (sesgo -9.6 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.4 / 17.1 / 0.5 / 32.8 K |
| p95 abs dT, celdas calientes | 4 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 122 % / 7 %, ×0.71 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 73 % / 32 %, ×1.04 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 5 % / 10 %, ×1.02 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 52 % / 45 %, ×0.73 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / -0.2 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×4.34 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 170 % |
| Error L1 del campo de calor liberado (celdas calientes) | 520 % |
| GA18 / OOD | 0.0 % / 3.4 % |
| Coste | 3.07 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 19.5 K, caliente 0.9 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5391 (1633) | 0.166 | 14 % | 14 % | 13 % |
| llama | 1187 (471) | 0.129 | 15 % | 18 % | 15 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.3 | 100 % | 100 % | – | – | 1480 / 1486 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.5 | 100 % | 103 % | – | – | 1480 / 1492 |
| 1.5 | arranque | 0 | – | – | 0.2 | 0.7 | 100 % | 535 % | – | – | 1480 / 1504 |
| 2.0 | arranque | 110 | 334.4 | +334.4 | 1.2 | 6.9 | 107 % | 7972 % | – | 522.65 | 1480 / 1894 |
| 2.5 | arranque | 164 | 236.9 | +236.9 | 1.5 | 8.8 | 102 % | 494 % | 2.06 | 2.22 | 1820 / 1972 |
| 3.0 | arranque | 197 | 53.4 | +29.7 | 0.8 | 4.4 | 97 % | 145 % | 1.26 | 1.94 | 2056 / 2004 |
| 3.5 | arranque | 230 | 40.0 | -2.7 | 0.7 | 3.3 | 96 % | 96 % | 1.11 | 2.38 | 2073 / 2015 |
| 4.0 | arranque | 264 | 35.5 | -13.2 | 0.6 | 2.7 | 96 % | 78 % | 1.09 | 2.61 | 2088 / 2029 |
| 4.5 | arranque | 292 | 33.2 | -19.5 | 0.6 | 2.4 | 96 % | 69 % | 1.06 | 2.77 | 2094 / 2036 |
| 5.0 | arranque | 321 | 32.4 | -23.4 | 0.6 | 2.4 | 96 % | 63 % | 1.03 | 2.98 | 2098 / 2039 |
| 7.5 | transicion | 462 | 27.8 | -26.6 | 0.6 | 2.5 | 94 % | 44 % | 0.99 | 3.29 | 2112 / 2063 |
| 10.0 | transicion | 596 | 22.8 | -22.8 | 0.6 | 2.7 | 93 % | 33 % | 0.99 | 3.47 | 2119 / 2069 |
| 12.5 | transicion | 734 | 19.5 | -19.2 | 0.7 | 3.3 | 92 % | 36 % | 1.00 | 3.71 | 2124 / 2074 |
| 15.0 | transicion | 865 | 17.4 | -16.4 | 0.8 | 3.7 | 91 % | 39 % | 1.00 | 3.87 | 2127 / 2081 |
| 17.5 | transicion | 996 | 16.6 | -14.4 | 1.0 | 4.3 | 94 % | 42 % | 1.00 | 4.02 | 2129 / 2086 |
| 20.0 | transicion | 1124 | 16.2 | -12.3 | 1.1 | 4.9 | 95 % | 46 % | 1.00 | 4.19 | 2131 / 2090 |
| 22.5 | transicion | 1256 | 16.0 | -10.8 | 1.2 | 5.5 | 110 % | 54 % | 1.01 | 4.29 | 2133 / 2095 |
| 25.0 | llama | 1390 | 15.9 | -9.6 | 1.4 | 6.2 | 122 % | 73 % | 1.01 | 4.34 | 2134 / 2099 |
