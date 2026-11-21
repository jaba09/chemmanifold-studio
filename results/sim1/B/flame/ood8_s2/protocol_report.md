# Protocolo CFD: ood8_s2

Modo: **pure**. Modelo: `/home/ubuntu/inputs/sim1-extra/models/ood8_s2`. Estado: completed 0.15 (hasta 150.0 ms). Puntuación **válida**.

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
| **Media abs dT en la llama** (T > 1600 K) | **23.0 K** (sesgo +3.8 K) |
| Deriva de ese error (100-150 ms) | +3.66 K cada 10 ms |
| Media abs dT en la llama, últimos 10 ms | 26.8 K |
| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | 34.8 / 56.1 / 20.3 / 34.8 K |
| p95 abs dT, celdas calientes | 171 K |
| OH: error L1 (calientes / llama), cantidad total modelo/DI | 51 % / 31 %, ×1.50 |
| CO: error L1 (calientes / llama), cantidad total modelo/DI | 36 % / 15 %, ×1.30 |
| CH4: error L1 (calientes / llama), cantidad total modelo/DI | 17 % / 23 %, ×0.83 |
| H: error L1 (calientes / llama), cantidad total modelo/DI | 100 % / 58 %, ×1.87 |
| Volumen por encima de 1500 K, modelo/DI | ×1.01 |
| Punta / base de la llama en el eje, modelo - DI | – / – mm |
| Calor liberado (GA18 evaluado en el estado) en la llama, modelo/DI | ×3.70 |
| Calor liberado fuera de la llama, en fracción del de la llama DI: DI / modelo | 6 % / 205 % |
| Error L1 del campo de calor liberado (celdas calientes) | 462 % |
| GA18 / OOD | 0.0 % / 27.1 % |
| Coste | 2.19 s por paso (4 procesos) |

Transición 5-25 ms (no puntúa): media abs dT llama – K, caliente – K, GA18 0.0 %.

## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)

| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |
|---|---|---|---|---|---|
| llama | 26922 (7801) | 0.103 | 15 % | 49 % | 3 % |

## Por instantánea

| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | L1 OH | L1 CO | V>1500 ×DI | calor llama ×DI | Tmax DI / modelo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100.0 | arranque | 4501 | 0.0 | +0.0 | 0.0 | 0.0 | 0 % | 0 % | 1.00 | 1.00 | 2123 / 2123 |
| 102.5 | llama | 4526 | 8.4 | -1.8 | 6.4 | 10.4 | 21 % | 4 % | 1.00 | 4.23 | 2123 / 2123 |
| 105.0 | llama | 4535 | 9.8 | -2.1 | 10.5 | 14.6 | 25 % | 4 % | 1.00 | 4.21 | 2123 / 2124 |
| 107.5 | llama | 4533 | 10.5 | -2.8 | 16.7 | 17.0 | 27 % | 7 % | 1.00 | 4.23 | 2123 / 2125 |
| 110.0 | llama | 4533 | 13.5 | -5.6 | 31.4 | 18.9 | 30 % | 16 % | 0.98 | 4.23 | 2123 / 2128 |
| 112.5 | llama | 4532 | 16.6 | -5.3 | 49.6 | 21.5 | 38 % | 29 % | 0.97 | 4.11 | 2123 / 2139 |
| 115.0 | llama | 4546 | 22.0 | -5.6 | 56.0 | 22.9 | 43 % | 37 % | 0.97 | 3.93 | 2123 / 2153 |
| 117.5 | llama | 4558 | 25.6 | -4.0 | 56.1 | 19.1 | 51 % | 43 % | 0.97 | 3.68 | 2123 / 2167 |
| 120.0 | llama | 4581 | 26.8 | -0.7 | 52.8 | 16.3 | 52 % | 45 % | 0.98 | 3.45 | 2123 / 2176 |
| 122.5 | llama | 4601 | 28.4 | +1.4 | 48.2 | 16.2 | 56 % | 48 % | 0.99 | 3.29 | 2123 / 2178 |
| 125.0 | llama | 4636 | 29.1 | +3.7 | 42.8 | 17.5 | 57 % | 49 % | 1.00 | 3.25 | 2123 / 2176 |
| 127.5 | llama | 4662 | 28.6 | +5.9 | 38.2 | 18.9 | 60 % | 49 % | 1.01 | 3.31 | 2123 / 2171 |
| 130.0 | llama | 4685 | 27.8 | +7.8 | 34.4 | 20.1 | 60 % | 46 % | 1.03 | 3.44 | 2123 / 2165 |
| 132.5 | llama | 4696 | 26.9 | +9.1 | 32.9 | 20.8 | 60 % | 45 % | 1.03 | 3.52 | 2123 / 2160 |
| 135.0 | llama | 4704 | 26.1 | +9.7 | 31.7 | 21.4 | 60 % | 44 % | 1.04 | 3.53 | 2123 / 2157 |
| 137.5 | llama | 4705 | 26.0 | +10.1 | 31.2 | 22.0 | 62 % | 44 % | 1.04 | 3.55 | 2122 / 2154 |
| 140.0 | llama | 4709 | 26.2 | +10.5 | 31.2 | 22.7 | 62 % | 44 % | 1.04 | 3.62 | 2122 / 2153 |
| 142.5 | llama | 4711 | 26.4 | +11.0 | 31.3 | 23.1 | 62 % | 44 % | 1.04 | 3.60 | 2122 / 2151 |
| 145.0 | llama | 4715 | 26.9 | +11.5 | 31.5 | 23.5 | 63 % | 44 % | 1.05 | 3.63 | 2121 / 2150 |
| 147.5 | llama | 4714 | 27.2 | +11.8 | 31.8 | 23.8 | 64 % | 43 % | 1.05 | 3.62 | 2121 / 2150 |
| 150.0 | llama | 4716 | 27.5 | +12.1 | 32.1 | 23.9 | 64 % | 42 % | 1.05 | 3.61 | 2121 / 2149 |
