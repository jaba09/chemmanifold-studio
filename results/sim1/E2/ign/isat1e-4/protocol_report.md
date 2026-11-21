# Protocolo CFD: isat1e-4

Modo: **di**. Modelo: `GA18 (DI)`. Estado: completed 0.025 (hasta 25.0 ms). Puntuación **válida**.

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.20 / -0.20 ms |
| Máximo exceso de Tmax del dominio sobre DI | +302 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +209 K |
| Media abs dT en la llama | 49.8 K |
| Media abs dT en la boquilla | 1.4 K |
| Media abs dT, celdas calientes | 0.3 K |
| Error L1 de OH, celdas calientes | 20 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **1.6 K** (sesgo +0.3 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.5 / 1.2 / 0.4 / 1.6 K |
| p95 abs dT, celdas calientes | 2 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 3 % / 1 %, ×1.02 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 0 %, ×1.00 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 0 % / 1 %, ×1.00 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 1 %, ×1.00 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.00 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 8 % |
| Error L1 del campo de calor liberado (celdas calientes) | 3 % |
| GA18 / OOD | – / – |
| Coste | 3.66 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 2.6 K, caliente 0.3 K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 11 % | 14 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 8 % | 19 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.1 | 10 % | 35 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.3 | 1.0 | 12 % | 843 % | – | – | 1480 / 1570 |
| 2.5 | arranque | 127 | 209.4 | +209.4 | 1.0 | 5.4 | 12 % | 155 % | 1.60 | 1.07 | 1820 / 2025 |
| 3.0 | arranque | 184 | 37.1 | +35.8 | 0.5 | 2.6 | 25 % | 34 % | 1.15 | 0.84 | 2056 / 2067 |
| 3.5 | arranque | 222 | 18.9 | +15.1 | 0.4 | 1.8 | 33 % | 27 % | 1.06 | 0.93 | 2073 / 2081 |
| 4.0 | arranque | 256 | 13.8 | +9.1 | 0.3 | 1.4 | 32 % | 21 % | 1.03 | 0.98 | 2088 / 2091 |
| 4.5 | arranque | 290 | 10.7 | +6.4 | 0.3 | 1.1 | 30 % | 16 % | 1.04 | 0.99 | 2094 / 2095 |
| 5.0 | arranque | 322 | 8.9 | +4.8 | 0.2 | 0.9 | 28 % | 13 % | 1.03 | 1.00 | 2098 / 2099 |
| 7.5 | transicion | 464 | 4.7 | +2.1 | 0.2 | 0.5 | 18 % | 5 % | 1.01 | 0.99 | 2112 / 2113 |
| 10.0 | transicion | 598 | 3.2 | +1.1 | 0.2 | 0.6 | 13 % | 3 % | 1.02 | 1.00 | 2119 / 2119 |
| 12.5 | transicion | 732 | 2.5 | +0.8 | 0.3 | 0.6 | 9 % | 2 % | 1.01 | 1.00 | 2124 / 2124 |
| 15.0 | transicion | 859 | 2.2 | +0.6 | 0.3 | 0.7 | 7 % | 1 % | 1.01 | 1.00 | 2127 / 2127 |
| 17.5 | transicion | 988 | 2.0 | +0.5 | 0.4 | 0.7 | 5 % | 1 % | 1.01 | 1.00 | 2129 / 2129 |
| 20.0 | transicion | 1109 | 1.8 | +0.4 | 0.4 | 0.7 | 4 % | 1 % | 1.01 | 1.00 | 2131 / 2131 |
| 22.5 | transicion | 1242 | 1.7 | +0.4 | 0.4 | 0.8 | 3 % | 1 % | 1.01 | 1.00 | 2133 / 2133 |
| 25.0 | llama | 1366 | 1.6 | +0.3 | 0.5 | 0.8 | 3 % | 1 % | 1.01 | 1.00 | 2134 / 2134 |
