# Protocolo CFD: P0_ood8

Modo: **pure**. Modelo: `/opt/ofb/models/P0_ood8`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 1.60 / -0.80 ms |
| Máximo exceso de Tmax del dominio sobre DI | +438 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +352 K |
| Media abs dT en la llama | 125.4 K |
| Media abs dT en la boquilla | 4.0 K |
| Media abs dT, celdas calientes | 0.9 K |
| Error L1 de OH, celdas calientes | 549 % |
| GA18 / OOD | 0.0 % / 0.0 % |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **10.8 K** (sesgo +0.9 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.7 / 4.9 / 0.3 / 6.2 K |
| p95 abs dT, celdas calientes | 4 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 72 % / 16 %, ×1.72 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 19 % / 6 %, ×0.87 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 3 %, ×1.00 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 17 % / 15 %, ×1.15 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.67 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 82 % |
| Error L1 del campo de calor liberado (celdas calientes) | 377 % |
| GA18 / OOD | 0.0 % / 0.2 % |
| Coste | 7.53 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 12.2 K, caliente 0.6 K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 4655 (659) | 0.0586 | 8 % | 11 % | 11 % |
| llama | 919 (142) | 0.0373 | 6 % | 12 % | 11 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.2 | 32 % | 100 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.4 | 140 % | 102 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 9 | 151.5 | +151.5 | 0.4 | 1.3 | 479 % | 2633 % | – | 2287.95 | 1480 / 1615 |
| 2.0 | arranque | 125 | 352.5 | +352.5 | 1.6 | 8.7 | 773 % | 8282 % | – | 302.11 | 1480 / 1908 |
| 2.5 | arranque | 173 | 245.6 | +245.6 | 1.9 | 9.7 | 833 % | 438 % | 2.16 | 2.01 | 1820 / 1985 |
| 3.0 | arranque | 206 | 77.2 | +51.0 | 1.3 | 5.6 | 791 % | 121 % | 1.30 | 1.85 | 2056 / 2012 |
| 3.5 | arranque | 240 | 56.5 | +19.1 | 1.1 | 4.4 | 720 % | 76 % | 1.15 | 2.26 | 2073 / 2024 |
| 4.0 | arranque | 275 | 46.3 | +8.7 | 1.0 | 3.7 | 642 % | 60 % | 1.13 | 2.44 | 2088 / 2033 |
| 4.5 | arranque | 307 | 39.1 | +3.6 | 0.9 | 3.2 | 570 % | 50 % | 1.10 | 2.54 | 2094 / 2044 |
| 5.0 | arranque | 332 | 34.4 | +0.2 | 0.9 | 2.9 | 506 % | 43 % | 1.07 | 2.69 | 2098 / 2051 |
| 7.5 | transicion | 472 | 20.6 | -3.8 | 0.7 | 2.2 | 301 % | 25 % | 1.02 | 2.90 | 2112 / 2071 |
| 10.0 | transicion | 604 | 15.1 | -4.5 | 0.6 | 2.0 | 203 % | 15 % | 1.02 | 3.10 | 2119 / 2083 |
| 12.5 | transicion | 738 | 12.0 | -4.2 | 0.6 | 1.9 | 149 % | 10 % | 1.01 | 3.23 | 2124 / 2090 |
| 15.0 | transicion | 860 | 9.3 | -3.5 | 0.5 | 1.8 | 119 % | 7 % | 1.01 | 3.32 | 2127 / 2097 |
| 17.5 | transicion | 989 | 8.8 | -3.5 | 0.6 | 2.0 | 102 % | 13 % | 1.00 | 3.46 | 2129 / 2103 |
| 20.0 | transicion | 1112 | 9.5 | -1.6 | 0.6 | 2.3 | 89 % | 20 % | 1.01 | 3.53 | 2131 / 2108 |
| 22.5 | transicion | 1245 | 10.3 | +0.1 | 0.7 | 2.7 | 79 % | 20 % | 1.01 | 3.61 | 2133 / 2113 |
| 25.0 | llama | 1372 | 10.8 | +0.9 | 0.7 | 3.1 | 72 % | 19 % | 1.01 | 3.67 | 2134 / 2117 |
