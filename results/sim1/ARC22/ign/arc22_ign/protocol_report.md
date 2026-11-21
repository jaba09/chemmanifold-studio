# Protocolo CFD: arc22_ign

Modo: **di**. Modelo: `GA18 (DI)`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.80 / +0.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +0 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -254 K |
| Media abs dT en la llama | 108.2 K |
| Media abs dT en la boquilla | 2.4 K |
| Media abs dT, celdas calientes | 0.5 K |
| Error L1 de OH, celdas calientes | 2 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **26.6 K** (sesgo -26.5 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 1.6 / 17.4 / 0.4 / 22.2 K |
| p95 abs dT, celdas calientes | 8 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 14 %, ×1.01 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 10 % / 11 %, ×0.90 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 9 % / 32 %, ×0.91 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 28 % / 28 %, ×1.17 |
| Volumen por encima de 1500 K, modelo/DI | ×0.97 |
| Punta / base de la llama en el eje, modelo - DI | -0.3 / +0.3 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×0.93 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 6 % |
| Error L1 del campo de calor liberado (celdas calientes) | 38 % |
| GA18 / OOD | – / – |
| Coste | 10.74 s por paso (8 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 27.2 K, caliente 1.1 K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.2 | 0.1 | 1 % | 1 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.1 | 1 % | 1 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.2 | 0.1 | 1 % | 2 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.2 | 1 % | 27 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 254.5 | -254.5 | 0.7 | 3.4 | 3 % | 84 % | 0.09 | 0.02 | 1820 / 1503 |
| 3.0 | arranque | 161 | 213.6 | -213.6 | 1.2 | 6.9 | 3 % | 69 % | 0.62 | 0.74 | 2056 / 1871 |
| 3.5 | arranque | 210 | 64.8 | -64.8 | 0.8 | 3.9 | 2 % | 34 % | 0.83 | 0.92 | 2073 / 2032 |
| 4.0 | arranque | 250 | 43.5 | -43.4 | 0.7 | 3.2 | 2 % | 20 % | 0.91 | 0.86 | 2088 / 2043 |
| 4.5 | arranque | 289 | 37.7 | -37.4 | 0.6 | 2.9 | 2 % | 15 % | 0.93 | 0.85 | 2094 / 2051 |
| 5.0 | arranque | 314 | 35.2 | -35.2 | 0.6 | 2.8 | 1 % | 12 % | 0.93 | 0.86 | 2098 / 2060 |
| 7.5 | transicion | 459 | 29.8 | -29.6 | 0.7 | 3.0 | 1 % | 8 % | 0.96 | 0.86 | 2112 / 2076 |
| 10.0 | transicion | 597 | 28.1 | -28.1 | 0.8 | 3.6 | 2 % | 8 % | 0.96 | 0.89 | 2119 / 2085 |
| 12.5 | transicion | 730 | 27.2 | -27.2 | 0.9 | 4.3 | 2 % | 8 % | 0.96 | 0.90 | 2124 / 2090 |
| 15.0 | transicion | 856 | 26.6 | -26.5 | 1.0 | 5.0 | 2 % | 8 % | 0.96 | 0.90 | 2127 / 2095 |
| 17.5 | transicion | 986 | 26.3 | -26.3 | 1.1 | 5.8 | 2 % | 9 % | 0.97 | 0.92 | 2129 / 2099 |
| 20.0 | transicion | 1108 | 26.1 | -26.1 | 1.3 | 6.6 | 2 % | 9 % | 0.96 | 0.92 | 2131 / 2102 |
| 22.5 | transicion | 1236 | 26.3 | -26.3 | 1.4 | 7.4 | 2 % | 10 % | 0.97 | 0.92 | 2133 / 2105 |
| 25.0 | llama | 1360 | 26.6 | -26.5 | 1.6 | 8.3 | 3 % | 10 % | 0.97 | 0.93 | 2134 / 2107 |
