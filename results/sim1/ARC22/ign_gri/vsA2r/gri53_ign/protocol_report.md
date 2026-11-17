# Protocolo CFD: gri53_ign

Modo: **di**. Modelo: `GA18 (DI)`. Estado: completed 0.005 (hasta 5.0 ms). Puntuación **no válida** (no llega a 25 ms).

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.80 / +0.40 ms |
| Máximo exceso de Tmax del dominio sobre DI | +0 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -257 K |
| Media abs dT en la llama | 103.4 K |
| Media abs dT en la boquilla | 2.3 K |
| Media abs dT, celdas calientes | 0.4 K |
| Error L1 de OH, celdas calientes | 1 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **– K** (sesgo – K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | – / – / – / – K |
| p95 abs dT, celdas calientes | – K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | – / –, ×– |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | – / –, ×– |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | – / –, ×– |
| H: error L1 (calientes / llama), cantidad total modelo/DI | – / –, ×– |
| Volumen por encima de 1500 K, modelo/DI | ×– |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×– |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | – / – |
| Error L1 del campo de calor liberado (celdas calientes) | – |
| GA18 / OOD | – / – |
| Coste | – s por paso (8 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.1 | 0.1 | 1 % | 1 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.1 | 0.1 | 0 % | 0 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.1 | 0.1 | 0 % | 1 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.1 | 0.2 | 0 % | 27 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 256.7 | -256.7 | 0.6 | 3.5 | 3 % | 84 % | 0.10 | 0.03 | 1820 / 1504 |
| 3.0 | arranque | 161 | 198.9 | -198.9 | 1.1 | 6.6 | 3 % | 67 % | 0.66 | 0.84 | 2056 / 1896 |
| 3.5 | arranque | 210 | 57.9 | -57.9 | 0.6 | 3.7 | 2 % | 31 % | 0.84 | 0.96 | 2073 / 2034 |
| 4.0 | arranque | 250 | 39.5 | -39.5 | 0.5 | 3.0 | 1 % | 18 % | 0.94 | 0.90 | 2088 / 2044 |
| 4.5 | arranque | 288 | 34.6 | -34.4 | 0.5 | 2.8 | 1 % | 13 % | 0.94 | 0.88 | 2094 / 2054 |
| 5.0 | arranque | 314 | 32.6 | -32.6 | 0.5 | 2.7 | 1 % | 11 % | 0.96 | 0.91 | 2098 / 2060 |
