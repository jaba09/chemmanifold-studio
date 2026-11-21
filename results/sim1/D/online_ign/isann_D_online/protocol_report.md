# Protocolo CFD: isann_D_online

Modo: **di**. Modelo: `GA18 (DI)`. Estado: running (hasta 25.0 ms). Puntuación **no válida** (no llega a 25 ms).

Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, nunca datos de entrenamiento.

## (a) Arranque, 0-5 ms

| Métrica | Valor |
|---|---|
| Tiempo de ignición (Tmax > 1600 K): DI / modelo / diferencia | 2.40 / 2.40 / +0.00 ms |
| Máximo exceso de Tmax del dominio sobre DI | +0 K |
| Sesgo de T en la llama (T > 1600 K), peor instantánea | +0 K |
| Media abs dT en la llama | 0.1 K |
| Media abs dT en la boquilla | 0.0 K |
| Media abs dT, celdas calientes | 0.0 K |
| Error L1 de OH, celdas calientes | 0 % |
| GA18 / OOD | – / – |

## (b) Llama establecida, 25-100 ms

| Métrica | Valor |
|---|---|
| **Media abs dT en la llama** (T > 1600 K) | **4.5 K** (sesgo +2.8 K) |
| Deriva de ese error (5-25 ms) | – K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | – K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 0.6 / 4.7 / 0.4 / 12.0 K |
| p95 abs dT, celdas calientes | 2 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 65 % / 4 %, ×0.37 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 11 % / 7 %, ×0.91 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 1 % / 4 %, ×1.01 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 12 % / 12 %, ×0.88 |
| Volumen por encima de 1500 K, modelo/DI | ×1.00 |
| Punta / base de la llama en el eje, modelo - DI | +0.0 / +0.0 mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×1.02 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 8 % / 4 % |
| Error L1 del campo de calor liberado (celdas calientes) | 27 % |
| GA18 / OOD | – / – |
| Coste | 3.94 s por paso (None procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama 3.1 K, caliente 0.3 K, GA18 –.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| transicion | 16526 (0) | 0.0128 | 2 % | 1 % | 7 % |
| llama | 3494 (0) | 0.00912 | 2 % | 1 % | 6 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | arranque | 0 | – | – | 0.0 | 0.0 | 0 % | 0 % | – | – | 1480 / 1480 |
| 1.0 | arranque | 0 | – | – | 0.0 | 0.0 | 0 % | 0 % | – | – | 1480 / 1480 |
| 1.5 | arranque | 0 | – | – | 0.0 | 0.0 | 0 % | 0 % | – | – | 1480 / 1480 |
| 2.0 | arranque | 0 | – | – | 0.0 | 0.0 | 0 % | 0 % | – | – | 1480 / 1480 |
| 2.5 | arranque | 63 | 0.2 | +0.2 | 0.0 | 0.0 | 0 % | 0 % | 1.01 | 1.00 | 1820 / 1820 |
| 3.0 | arranque | 161 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2056 / 2056 |
| 3.5 | arranque | 210 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2073 / 2073 |
| 4.0 | arranque | 250 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2088 / 2088 |
| 4.5 | arranque | 288 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2094 / 2094 |
| 5.0 | arranque | 314 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2098 / 2098 |
| 7.5 | transicion | 460 | 0.1 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2112 / 2112 |
| 10.0 | transicion | 597 | 2.3 | +2.3 | 0.2 | 0.3 | 41 % | 2 % | 1.00 | 0.93 | 2119 / 2126 |
| 12.5 | transicion | 731 | 2.7 | +2.7 | 0.3 | 0.6 | 70 % | 5 % | 1.00 | 0.92 | 2124 / 2133 |
| 15.0 | transicion | 860 | 3.9 | +3.9 | 0.4 | 1.0 | 69 % | 7 % | 1.00 | 0.99 | 2127 / 2136 |
| 17.5 | transicion | 990 | 4.2 | +4.1 | 0.4 | 1.2 | 67 % | 8 % | 1.00 | 0.97 | 2129 / 2139 |
| 20.0 | transicion | 1110 | 4.2 | +3.7 | 0.5 | 1.4 | 66 % | 10 % | 1.00 | 1.01 | 2131 / 2142 |
| 22.5 | transicion | 1242 | 4.2 | +3.2 | 0.5 | 1.7 | 65 % | 11 % | 1.00 | 1.01 | 2133 / 2143 |
| 25.0 | llama | 1369 | 4.5 | +2.8 | 0.6 | 1.9 | 65 % | 11 % | 1.00 | 1.02 | 2134 / 2143 |
