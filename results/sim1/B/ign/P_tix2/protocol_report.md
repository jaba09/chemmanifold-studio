# Protocolo CFD: P_tix2

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.00 / -0.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +283 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +216 K |
| Media abs dT en la llama | 97.6 K |
| Media abs dT en la boquilla | 3.0 K |
| Media abs dT, celdas calientes | 0.6 K |
| Error L1 de OH, celdas calientes | 97 % |
| GA18 / OOD | 0.0 % / 0.4 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **14.9 K** (sesgo -10.5 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.9 / 4.8 / 0.3 / 6.2 K |
| p95 abs dT, celdas calientes | 4 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 43 % / 21 %, ×1.12 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 11 % / 6 %, ×1.10 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 4 % / 8 %, ×0.98 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 66 % / 65 %, ×1.66 |
| Volumen por encima de 1500 K, modelo/DI | ×1.02 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×2.44 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 19 % |
| Error L1 del campo de calor liberado (celdas calientes) | 174 % |
| GA18 / OOD | 0.0 % / 0.1 % |
| Coste | 4.64 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 23.7 K, caliente 0.8 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4752 (143) | 0.0219 | 4 % | 2 % | 7 % |
| llama | 879 (24) | 0.019 | 4 % | 2 % | 5 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 100 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 99 % | 100 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 99 % | 111 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 38 | 216.2 | +216.2 | 0.5 | 2.3 | 101 % | 2286 % | – | 396.66 | 1480 / 1700 |
| 2.5 | arranque | 161 | 187.1 | +187.1 | 1.2 | 6.9 | 100 % | 345 % | 1.95 | 1.76 | 1820 / 1874 |
| 3.0 | arranque | 206 | 68.0 | +12.6 | 0.9 | 4.7 | 95 % | 91 % | 1.30 | 1.57 | 2056 / 1935 |
| 3.5 | arranque | 241 | 60.6 | -7.6 | 0.8 | 4.2 | 95 % | 54 % | 1.19 | 1.78 | 2073 / 1962 |
| 4.0 | arranque | 277 | 54.9 | -14.1 | 0.7 | 3.9 | 95 % | 40 % | 1.14 | 1.85 | 2088 / 1977 |
| 4.5 | arranque | 311 | 49.7 | -16.5 | 0.7 | 3.6 | 95 % | 33 % | 1.11 | 1.90 | 2094 / 1994 |
| 5.0 | arranque | 336 | 46.5 | -18.3 | 0.7 | 3.5 | 95 % | 28 % | 1.09 | 1.94 | 2098 / 2002 |
| 7.5 | transicion | 475 | 35.5 | -19.0 | 0.7 | 3.3 | 93 % | 18 % | 1.05 | 1.88 | 2112 / 2029 |
| 10.0 | transicion | 613 | 29.4 | -17.6 | 0.8 | 3.4 | 81 % | 14 % | 1.04 | 1.93 | 2119 / 2044 |
| 12.5 | transicion | 747 | 25.2 | -15.7 | 0.8 | 3.5 | 64 % | 12 % | 1.02 | 1.97 | 2124 / 2057 |
| 15.0 | transicion | 869 | 22.2 | -14.3 | 0.8 | 3.6 | 50 % | 11 % | 1.02 | 2.04 | 2127 / 2066 |
| 17.5 | transicion | 1002 | 19.7 | -13.0 | 0.8 | 3.7 | 32 % | 11 % | 1.02 | 2.14 | 2129 / 2074 |
| 20.0 | transicion | 1122 | 17.8 | -12.0 | 0.8 | 3.7 | 24 % | 11 % | 1.01 | 2.23 | 2131 / 2080 |
| 22.5 | transicion | 1251 | 16.1 | -11.1 | 0.8 | 3.8 | 36 % | 11 % | 1.01 | 2.34 | 2133 / 2086 |
| 25.0 | llama | 1372 | 14.9 | -10.5 | 0.9 | 3.9 | 43 % | 11 % | 1.02 | 2.44 | 2134 / 2090 |
