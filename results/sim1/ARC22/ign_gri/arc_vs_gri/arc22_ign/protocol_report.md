# Protocolo CFD: arc22_ign

Modo: **di**. Modelo: `GA18 (DI)`. Estado: completed 0.025 (hasta 5.0 ms). Puntuación **no válida** (no llega a 25 ms).

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.80 / 2.80 / +0.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +1 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | -20 K |
| Media abs dT en la llama | 12.1 K |
| Media abs dT en la boquilla | 0.5 K |
| Media abs dT, celdas calientes | 0.3 K |
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
| Coste | 10.74 s por paso (8 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 –.

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.3 | 0.2 | 1 % | 1 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.2 | 0.2 | 1 % | 1 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.2 | 0.3 | 1 % | 1 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.2 | 0.3 | 1 % | 1 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 0 | – | – | 0.3 | 0.3 | 1 % | 4 % | 0.85 | – | 1504 / 1503 |
| 3.0 | arranque | 90 | 20.3 | -20.3 | 0.3 | 0.6 | 1 % | 7 % | 0.94 | 0.91 | 1896 / 1871 |
| 3.5 | arranque | 182 | 11.5 | -6.7 | 0.3 | 0.6 | 1 % | 5 % | 0.98 | 0.97 | 2034 / 2032 |
| 4.0 | arranque | 226 | 10.3 | -4.2 | 0.3 | 0.7 | 1 % | 4 % | 0.97 | 0.95 | 2044 / 2043 |
| 4.5 | arranque | 266 | 9.5 | -3.4 | 0.3 | 0.7 | 1 % | 3 % | 0.99 | 0.96 | 2054 / 2051 |
| 5.0 | arranque | 296 | 9.1 | -2.8 | 0.4 | 0.8 | 1 % | 3 % | 0.98 | 0.95 | 2060 / 2060 |
