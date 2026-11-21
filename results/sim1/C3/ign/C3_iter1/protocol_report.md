# Protocolo CFD: C3_iter1

Modo: **pure**. Modelo: `/opt/ofb/iterml_v2/iter1/ensemble`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.80 / +0.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +0 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -258 K |
| Media abs dT en la llama | 80.3 K |
| Media abs dT en la boquilla | 1.5 K |
| Media abs dT, celdas calientes | 0.4 K |
| Error L1 de OH, celdas calientes | 64 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **28.0 K** (sesgo -12.4 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 23.1 / 20.7 / 23.0 / 21.3 K |
| p95 abs dT, celdas calientes | 204 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 135 % / 12 %, ×2.30 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 187 % / 8 %, ×2.80 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 17 % / 9 %, ×1.12 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 36 % / 22 %, ×1.31 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | -0.3 / -0.2 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.35 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 241 % |
| Error L1 del campo de calor liberado (celdas calientes) | 252 % |
| GA18 / OOD | 0.0 % / 2.3 % |
| Coste | 6.74 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 16.5 K, caliente 11.5 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 5044 (671) | 0.0597 | 9 % | 1 % | 6 % |
| llama | 980 (179) | 0.0852 | 12 % | 1 % | 10 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 135 % | 227 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 5 % | 428 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.2 | 41 % | 610 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.3 | 55 % | 526 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 257.6 | -257.6 | 0.7 | 3.6 | 64 % | 118 % | 0.00 | 0.03 | 1820 / 1490 |
| 3.0 | arranque | 161 | 126.9 | -126.9 | 0.9 | 4.6 | 65 % | 60 % | 0.71 | 1.42 | 2056 / 1981 |
| 3.5 | arranque | 210 | 34.5 | -29.1 | 0.5 | 2.1 | 67 % | 24 % | 0.89 | 1.25 | 2073 / 2061 |
| 4.0 | arranque | 251 | 24.4 | -16.8 | 0.4 | 1.6 | 69 % | 16 % | 0.95 | 1.19 | 2088 / 2075 |
| 4.5 | arranque | 288 | 20.2 | -13.0 | 0.4 | 1.4 | 71 % | 13 % | 0.98 | 1.18 | 2094 / 2085 |
| 5.0 | arranque | 315 | 18.1 | -11.7 | 0.4 | 1.3 | 73 % | 12 % | 0.97 | 1.20 | 2098 / 2090 |
| 7.5 | transicion | 460 | 13.8 | -9.7 | 0.4 | 1.4 | 78 % | 13 % | 0.99 | 1.22 | 2112 / 2103 |
| 10.0 | transicion | 598 | 12.9 | -9.4 | 0.7 | 1.7 | 41 % | 21 % | 0.99 | 1.24 | 2119 / 2109 |
| 12.5 | transicion | 733 | 12.6 | -9.5 | 2.2 | 2.3 | 348 % | 48 % | 1.00 | 1.27 | 2124 / 2112 |
| 15.0 | transicion | 860 | 14.3 | -10.1 | 14.7 | 3.0 | 272 % | 57 % | 0.99 | 1.28 | 2127 / 2114 |
| 17.5 | transicion | 991 | 17.5 | -10.7 | 18.8 | 4.2 | 194 % | 76 % | 0.99 | 1.31 | 2129 / 2116 |
| 20.0 | transicion | 1119 | 20.4 | -11.4 | 21.3 | 6.0 | 160 % | 111 % | 0.98 | 1.31 | 2131 / 2118 |
| 22.5 | transicion | 1253 | 24.2 | -12.1 | 22.6 | 8.5 | 144 % | 153 % | 0.99 | 1.34 | 2133 / 2120 |
| 25.0 | llama | 1388 | 28.0 | -12.4 | 23.1 | 11.2 | 135 % | 187 % | 1.00 | 1.35 | 2134 / 2120 |
