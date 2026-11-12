# Protocolo CFD: tix2_s1

Modo: **pure**. Modelo: `/home/ubuntu/chemmanifold-studio/data/openfoam_tix2_seeds/s1/08_fluent/resnet_film`. Estado: failed 0.11 (hasta 110.0 ms). Puntuación **no válida** (no llega a 150 ms).

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | – / 100.20 / – ms |
| Máximo exceso de Tmax del dominio sobre DI | – K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +0 K |
| Media abs dT en la llama | 0.0 K |
| Media abs dT en la boquilla | 0.0 K |
| Media abs dT, celdas calientes | 0.0 K |
| Error L1 de OH, celdas calientes | 0 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **105.9 K** (sesgo -20.7 K) |
| Deriva de ese error (100-150 ms) | +302.55 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 104.2 / 124.8 / 52.4 / 240.0 K |
| p95 abs dT, celdas calientes | 468 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 65 % / 67 %, ×1.36 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 31 % / 26 %, ×1.17 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 43 % / 55 %, ×0.68 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 173 % / 113 %, ×2.33 |
| Volumen por encima de 1500 K, modelo/DI | ×0.94 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×23.81 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 7 % / 62259 % |
| Error L1 del campo de calor liberado (celdas calientes) | 60297 % |
| GA18 / OOD | 0.0 % / 13.3 % |
| Coste | 2.20 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 5570 (2524) | 0.253 | 20 % | 45 % | 8 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4513 | 21.5 | -18.9 | 11.4 | 24.1 | 39 % | 10 % | 1.00 | 9.38 | 2123 / 2113 |
| 105.0 | llama | 4584 | 41.0 | -21.8 | 43.7 | 123.3 | 54 % | 19 % | 0.98 | 9.65 | 2123 / 2117 |
| 107.5 | llama | 4704 | 110.7 | -18.6 | 121.6 | 310.3 | 72 % | 38 % | 0.93 | 13.40 | 2123 / 2119 |
| 110.0 | llama | 5003 | 250.4 | -23.3 | 240.2 | 435.4 | 94 % | 59 % | 0.87 | 62.82 | 2123 / 2145 |
