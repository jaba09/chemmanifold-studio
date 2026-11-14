# Protocolo CFD: P_tix2all

Modo: **pure**. Modelo: `/opt/ofb/models/P_tix2all`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.00 / -0.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +301 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +219 K |
| Media abs dT en la llama | 100.0 K |
| Media abs dT en la boquilla | 3.2 K |
| Media abs dT, celdas calientes | 0.6 K |
| Error L1 de OH, celdas calientes | 95 % |
| GA18 / OOD | 0.0 % / 0.1 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **14.7 K** (sesgo -14.0 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.1 / 17.0 / 0.3 / 31.5 K |
| p95 abs dT, celdas calientes | 3 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 34 % / 23 %, ×1.01 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 15 % / 10 %, ×1.10 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 13 % / 19 %, ×0.90 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 48 % / 46 %, ×1.47 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.85 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 711 % |
| Error L1 del campo de calor liberado (celdas calientes) | 917 % |
| GA18 / OOD | 0.0 % / 0.0 % |
| Coste | 7.74 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 20.9 K, caliente 0.8 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4775 (310) | 0.0321 | 5 % | 2 % | 6 % |
| llama | 846 (43) | 0.0298 | 4 % | 7 % | 5 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 99 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 99 % | 100 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 98 % | 123 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 60 | 219.4 | +219.4 | 0.6 | 3.0 | 102 % | 3013 % | – | 703.38 | 1480 / 1707 |
| 2.5 | arranque | 158 | 182.5 | +182.5 | 1.2 | 7.1 | 99 % | 395 % | 1.99 | 2.26 | 1820 / 1874 |
| 3.0 | arranque | 206 | 74.4 | +14.5 | 0.9 | 5.0 | 94 % | 114 % | 1.31 | 2.22 | 2056 / 1935 |
| 3.5 | arranque | 246 | 65.9 | -5.0 | 0.9 | 4.6 | 93 % | 69 % | 1.19 | 2.61 | 2073 / 1964 |
| 4.0 | arranque | 277 | 58.4 | -13.0 | 0.8 | 4.2 | 91 % | 52 % | 1.15 | 2.79 | 2088 / 1977 |
| 4.5 | arranque | 312 | 51.8 | -15.5 | 0.8 | 3.8 | 88 % | 42 % | 1.11 | 2.89 | 2094 / 1991 |
| 5.0 | arranque | 336 | 47.4 | -17.3 | 0.8 | 3.6 | 84 % | 36 % | 1.09 | 2.98 | 2098 / 2000 |
| 7.5 | transicion | 473 | 34.2 | -19.7 | 0.7 | 3.3 | 49 % | 22 % | 1.04 | 3.11 | 2112 / 2024 |
| 10.0 | transicion | 608 | 26.7 | -19.0 | 0.7 | 3.2 | 34 % | 17 % | 1.03 | 3.22 | 2119 / 2041 |
| 12.5 | transicion | 740 | 21.5 | -17.9 | 0.7 | 3.2 | 32 % | 14 % | 1.01 | 3.36 | 2124 / 2053 |
| 15.0 | transicion | 862 | 17.8 | -16.1 | 0.7 | 3.4 | 32 % | 13 % | 1.01 | 3.44 | 2127 / 2063 |
| 17.5 | transicion | 990 | 16.0 | -15.1 | 0.8 | 3.9 | 31 % | 13 % | 1.00 | 3.57 | 2129 / 2071 |
| 20.0 | transicion | 1113 | 15.2 | -14.3 | 0.9 | 4.6 | 31 % | 13 % | 1.00 | 3.63 | 2131 / 2077 |
| 22.5 | transicion | 1241 | 15.1 | -14.2 | 1.0 | 5.2 | 33 % | 14 % | 1.00 | 3.75 | 2133 / 2083 |
| 25.0 | llama | 1367 | 14.7 | -14.0 | 1.1 | 5.8 | 34 % | 15 % | 1.00 | 3.85 | 2134 / 2088 |
