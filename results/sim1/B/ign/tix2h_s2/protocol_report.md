# Protocolo CFD: tix2h_s2

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2h_seeds/s2/08_fluent/resnet_film`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 5.20 / +2.80 ms |
| Máximo exceso de Tmax del dominio sobre DI | +0 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -437 K |
| Media abs dT en la llama | 403.8 K |
| Media abs dT en la boquilla | 10.4 K |
| Media abs dT, celdas calientes | 1.7 K |
| Error L1 de OH, celdas calientes | 85 % |
| GA18 / OOD | 0.0 % / 39.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **23.5 K** (sesgo -16.1 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 7.3 / 22.3 / 6.1 / 115.2 K |
| p95 abs dT, celdas calientes | 29 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 86 % / 33 %, ×0.35 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 386 % / 15 %, ×4.81 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 137 % / 30 %, ×2.06 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 62 % / 57 %, ×1.61 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | -0.3 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×4.70 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / -19 % |
| Error L1 del campo de calor liberado (celdas calientes) | 636 % |
| GA18 / OOD | 0.0 % / 2.1 % |
| Coste | 3.18 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 28.1 K, caliente 3.1 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4963 (599) | 0.0651 | 10 % | 4 % | 7 % |
| llama | 915 (137) | 0.0646 | 11 % | 3 % | 5 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 100 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.2 | 99 % | 100 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.3 | 99 % | 101 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.4 | 98 % | 101 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 277.0 | -277.0 | 0.7 | 4.0 | 97 % | 99 % | 0.00 | 0.00 | 1820 / 1480 |
| 3.0 | arranque | 161 | 420.2 | -420.2 | 2.0 | 12.2 | 90 % | 99 % | 0.00 | 0.00 | 2056 / 1480 |
| 3.5 | arranque | 210 | 434.3 | -434.3 | 2.7 | 16.8 | 74 % | 98 % | 0.00 | 0.00 | 2073 / 1480 |
| 4.0 | arranque | 250 | 437.2 | -437.2 | 3.3 | 20.5 | 61 % | 98 % | 0.00 | 0.00 | 2088 / 1480 |
| 4.5 | arranque | 288 | 434.2 | -434.2 | 3.8 | 23.5 | 60 % | 98 % | 0.00 | 0.01 | 2094 / 1480 |
| 5.0 | arranque | 314 | 419.7 | -419.7 | 4.1 | 25.4 | 69 % | 98 % | 0.12 | 0.37 | 2098 / 1542 |
| 7.5 | transicion | 462 | 46.5 | -45.4 | 1.6 | 5.5 | 106 % | 50 % | 0.92 | 3.36 | 2112 / 2027 |
| 10.0 | transicion | 597 | 32.6 | -31.8 | 1.7 | 4.6 | 85 % | 152 % | 0.97 | 3.54 | 2119 / 2046 |
| 12.5 | transicion | 731 | 26.1 | -25.9 | 1.6 | 4.1 | 112 % | 194 % | 0.99 | 3.74 | 2124 / 2057 |
| 15.0 | transicion | 856 | 22.2 | -22.0 | 2.6 | 4.6 | 108 % | 246 % | 1.00 | 3.88 | 2127 / 2064 |
| 17.5 | transicion | 991 | 22.3 | -18.4 | 4.0 | 6.8 | 98 % | 315 % | 1.00 | 4.07 | 2129 / 2071 |
| 20.0 | transicion | 1114 | 23.7 | -16.9 | 4.7 | 8.2 | 87 % | 355 % | 1.00 | 4.31 | 2131 / 2078 |
| 22.5 | transicion | 1238 | 23.6 | -16.4 | 5.7 | 9.6 | 89 % | 366 % | 0.99 | 4.55 | 2133 / 2084 |
| 25.0 | llama | 1365 | 23.5 | -16.1 | 7.3 | 11.2 | 86 % | 386 % | 0.99 | 4.70 | 2134 / 2088 |
