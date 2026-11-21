# Protocolo CFD: tix2_s2

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2_seeds/s2/08_fluent/resnet_film`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.20 / -0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +214 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +139 K |
| Media abs dT en la llama | 75.2 K |
| Media abs dT en la boquilla | 85.3 K |
| Media abs dT, celdas calientes | 109.5 K |
| Error L1 de OH, celdas calientes | 98 % |
| GA18 / OOD | 0.0 % / 86.7 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **42.5 K** (sesgo -27.0 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 24.3 / 32.8 / 23.5 / 30.7 K |
| p95 abs dT, celdas calientes | 97 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 131 % / 26 %, ×2.16 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 144 % / 11 %, ×2.34 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 39 % / 11 %, ×1.30 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 158 % / 134 %, ×2.58 |
| Volumen por encima de 1500 K, modelo/DI | ×0.99 |
| Punta / base de la llama en el eje, modelo - DI | -0.5 / -0.2 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.24 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 259 % |
| Error L1 del campo de calor liberado (celdas calientes) | 440 % |
| GA18 / OOD | 0.0 % / 1.8 % |
| Coste | 2.98 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 46.0 K, caliente 42.4 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5073 (1039) | 0.212 | 24 % | 6 % | 22 % |
| llama | 983 (223) | 0.128 | 22 % | 5 % | 21 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 100 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 1.8 | 2.4 | 100 % | 100 % | – | – | 1480 / 1479 |
| 1.5 | arranque | 0 | – | – | 12.3 | 12.9 | 100 % | 112 % | – | – | 1480 / 1471 |
| 2.0 | arranque | 0 | – | – | 51.9 | 47.1 | 100 % | 564 % | – | – | 1480 / 1509 |
| 2.5 | arranque | 132 | 139.4 | +138.8 | 108.5 | 96.2 | 100 % | 189 % | 1.50 | 2.14 | 1820 / 1890 |
| 3.0 | arranque | 198 | 67.2 | -6.6 | 146.0 | 123.0 | 96 % | 47 % | 1.20 | 1.48 | 2056 / 1939 |
| 3.5 | arranque | 241 | 65.7 | -21.2 | 172.3 | 139.0 | 96 % | 24 % | 1.12 | 1.45 | 2073 / 1957 |
| 4.0 | arranque | 280 | 63.2 | -23.8 | 191.1 | 147.0 | 97 % | 22 % | 1.12 | 1.44 | 2088 / 1979 |
| 4.5 | arranque | 313 | 59.9 | -25.7 | 202.6 | 146.3 | 97 % | 20 % | 1.11 | 1.42 | 2094 / 1989 |
| 5.0 | arranque | 347 | 55.5 | -24.6 | 208.5 | 139.0 | 98 % | 21 % | 1.10 | 1.39 | 2098 / 1998 |
| 7.5 | transicion | 474 | 43.7 | -30.7 | 163.2 | 60.9 | 120 % | 86 % | 1.05 | 1.06 | 2112 / 2017 |
| 10.0 | transicion | 614 | 48.0 | -33.2 | 37.4 | 12.2 | 1336 % | 6522 % | 1.01 | 0.72 | 2119 / 2031 |
| 12.5 | transicion | 751 | 48.5 | -31.6 | 16.3 | 9.7 | 588 % | 1074 % | 1.02 | 0.52 | 2124 / 2041 |
| 15.0 | transicion | 883 | 48.2 | -31.3 | 17.5 | 12.1 | 310 % | 536 % | 0.99 | 0.31 | 2127 / 2045 |
| 17.5 | transicion | 1011 | 45.9 | -30.5 | 19.3 | 12.3 | 215 % | 341 % | 0.99 | 0.23 | 2129 / 2052 |
| 20.0 | transicion | 1135 | 44.7 | -29.4 | 21.1 | 13.0 | 181 % | 241 % | 0.99 | 0.17 | 2131 / 2057 |
| 22.5 | transicion | 1263 | 43.2 | -29.3 | 22.3 | 15.0 | 152 % | 182 % | 0.98 | 0.18 | 2133 / 2061 |
| 25.0 | llama | 1395 | 42.5 | -27.0 | 24.3 | 15.1 | 131 % | 144 % | 0.99 | 0.24 | 2134 / 2066 |
