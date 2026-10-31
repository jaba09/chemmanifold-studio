# Protocolo CFD fijo de evaluación de surrogados (quemador GA18, OpenFOAM)

Versión 1, 30 de octubre de 2026. Parámetros exactos en `protocol.yaml`; si cambia algo, sube el número
de versión, porque los informes de versiones distintas no se comparan.

**Regla:** los estados CFD de este protocolo (DI, híbridos, puros, DI en sombra) son solo diagnóstico y
evaluación. Nunca entran en el entrenamiento ni en la elección de los datos de exploración por sí solos.

## Para qué

Hasta ahora cada modelo se juzgaba con una corrida híbrida de 25 ms y la media de |dT| de la llama. Eso
tiene tres problemas: 25 ms no deja ver la deriva lenta (ood6 parecía bueno a 25 ms y se fue a 23 K a
47 ms), el arranque artificial (gas pobre a 1480 K) se mezcla con la llama, y el híbrido premia al
modelo que más delega en GA18. Fluent no tiene modo híbrido, así que el modelo final tiene que aguantar
solo. Este protocolo fija una prueba más larga, igual para todos, con el arranque y la llama puntuados
por separado y una corrida sin GA18.

## La prueba

| | |
|---|---|
| Caso | quemador `quemadorUnico` (malla de Fluent, GA18, 2D axisimétrico), OpenFOAM v2412, `rhoReactingBuoyantFoam` |
| Arranque | encendido, el mismo del bucle OOD: gas quemado pobre phi 0,5 a 1480 K en `fff-fluid-fuel` y `fff-fluid-mixing`, aire a 300 K en el resto. No es el estado estacionario de la DI. |
| Paso | Euler, dt 2e-5 s fijo, PIMPLE 1 corrección externa y 2 de presión |
| Duración | 100 ms (5000 pasos). Una corrida que no llega a 50 ms no tiene puntuación válida. |
| Escrituras | cada 0,5 ms hasta 5 ms, después cada 2,5 ms. Tmax del dominio cada 10 pasos. |
| Procesos | 2 (el coste en s por paso solo se compara con el mismo número) |
| Química | `userChemStep`: T_freeze 600 K, maxSubsteps 50, checkOOD; DI en sombra cada 50 pasos, 2 celdas por banda (T, Z, dentro/OOD) |
| Modos | **puro**: el surrogado en todas las celdas, las OOD solo se cuentan (como en Fluent). **híbrido**: GA18 en las celdas OOD. |
| Referencia | GA18 DI (ODE seulex) con el mismo arranque, dt y escrituras |

Cada modelo candidato se corre en modo **puro**. El modo híbrido es opcional y sirve para ver cuánto
depende el modelo de GA18; no sustituye a la corrida pura.

## Fases

| Fase | Ventana | Qué mide |
|---|---|---|
| (a) Arranque | 0-5 ms, 10 instantáneas | ignición del chorro de CH4 en el gas inicial caliente: el defecto de ignición temprana |
| Transición | 5-22,5 ms | se informa, no puntúa |
| (b) Llama establecida | 25-100 ms, 31 instantáneas | la llama ya formada creciendo sobre el chorro: error, deriva y especies |

La llama de la DI sigue creciendo hasta 50 ms o más (950 celdas por encima de 1600 K a 25 ms, 1900 a
50 ms), así que la fase (b) no es un estado estacionario. Se compara instantánea a instantánea con la DI
en el mismo tiempo.

## Zonas fijas

Las zonas de estado se clasifican con el estado de la **DI**, de modo que un modelo no puede mover celdas
de una zona a otra y la población de cada zona es la misma para todos los modelos.

| Zona | Celdas |
|---|---|
| caliente | T > 600 K en la DI o en el modelo |
| llama | T > 1600 K en la DI o en el modelo |
| reactiva | caliente, no llama, Z de la DI entre 0,03 y 0,3 |
| gas quemado pobre | caliente, no llama, Z < 0,03 (el gas inicial y sus productos diluidos y enfriados) |
| rica | caliente, no llama, Z > 0,3 |
| boquilla | caliente, x < 30 mm y r < 15 mm (donde nace la llama) |

## Métricas

Por instantánea, frente a la DI en el mismo tiempo:

- **T:** media de |dT| y sesgo (media de dT con signo) en cada zona; p95 y máximo en las calientes.
- **Especies OH, CO, CH4 y H:** error L1 relativo ponderado por volumen, sum(V |Y - Y_DI|) / sum(V Y_DI),
  en las celdas calientes y en la llama; y la razón de cantidades totales (por ejemplo OH ×2).
- **Forma de la llama:** volumen por encima de 1500 K (razón modelo/DI) y base y punta de la isoterma
  de 1500 K en el eje (r < 2 mm).
- **Calor liberado:** el de GA18 evaluado con Cantera en el estado de cada corrida. Se da la razón
  modelo/DI en las celdas de llama, el calor liberado fuera de la llama como fracción del de la llama
  DI (en la DI es casi cero; si el modelo deja el gas quemado lejos del equilibrio, por ejemplo con H u
  OH de más, aquí sale grande) y el error L1 del campo. Mide si el estado del modelo es químicamente el
  mismo, no el calor que el surrogado aplicó. El total sobre todas las celdas calientes no se usa: el
  gran volumen de gas quemado casi se cancela y la razón queda mal condicionada.
- **GA18 y OOD:** fracción de celdas avanzadas que fueron a GA18 (híbrido) o salieron como OOD.
- **Coste:** mediana de s por paso.

Resumen de cada fase:

- **(a) Arranque:** tiempo de ignición (primer paso con Tmax del dominio > 1600 K) del modelo menos el de
  la DI; máximo exceso de Tmax sobre la DI; sesgo de T de la llama en la peor instantánea y media de |dT|
  de la llama; |dT| en la boquilla y en las calientes; error de OH.
- **(b) Llama establecida:** media en el tiempo de |dT| de la llama (**la cifra principal**) y su sesgo;
  **deriva** = pendiente de un ajuste lineal de ese error entre 25 y 100 ms, en K cada 10 ms; el mismo
  error en los últimos 10 ms; |dT| por zona; errores de especies; volumen caliente, punta y base;
  calor liberado; GA18, OOD y coste.
- **DI en sombra:** medianas por fase del error de un paso (|dT| y error relativo del incremento de T,
  OH y CO), dentro y fuera de los datos.

Ruido de la referencia: la DI repetida con el mismo arranque coincide con la del bucle OOD a 0,01 K de
media (máximo 4 K) a 2,5 y 5 ms. Diferencias por debajo de eso no significan nada.

Referencias orientativas, no un aprobado: llama < 10 K, deriva < 1 K cada 10 ms, ignición a menos de
0,25 ms de la DI, OH L1 < 50 %.

## Cómo se corre

Con el entorno de OpenFOAM cargado y `libuserChemStep` compilada:

```sh
P=openfoam/protocol
# referencia DI, una vez (reanudable)
LABEL=di $P/run_protocol.sh <caso base> runs/di di
# un modelo, sin GA18 y en híbrido (reanudable: repetir la orden tras un reinicio)
$P/run_protocol.sh <caso base> runs/ood1_puro   pure   <carpeta 08_fluent del modelo>
$P/run_protocol.sh <caso base> runs/ood1_hibrido hybrid <carpeta 08_fluent del modelo>
# informe estándar (Python con numpy, pandas, pyyaml, matplotlib y cantera)
python $P/score_protocol.py --di runs/di/snap --run runs/ood1_puro/snap --label ood1_puro \
    --run-dir runs/ood1_puro --di-dir runs/di --out informes
# tabla de comparación de varios modelos
python $P/score_protocol.py --compare informes/*/protocol_report.json --out informes
```

`run_protocol.sh` deja en `<run>/snap/` las instantáneas en CSV (formato de exportación de Fluent,
`openfoam/tools/foam_snapshot.py`) y en `<run>/protocol_status` si terminó (`completed`) o en qué tiempo
falló. Una corrida pura que diverge queda puntuada hasta donde llegó y marcada como no válida si no
pasa de 50 ms.

Una DI de referencia ya hecha se puede extender desde su último estado:
`LABEL=di run_protocol.sh <caso base> runs/di_ext di "" 2 <dir del tiempo 0.05>`; `--di` acepta varias
carpetas de instantáneas.

Salida de `score_protocol.py` en `<out>/<label>/`: `protocol_report.md` (tablas de las dos fases, DI en
sombra y una fila por instantánea), `protocol_report.json` (todo, con los parámetros del protocolo) y
`protocol_timeseries.png` (errores, especies, volumen y calor, GA18/OOD frente al tiempo).

Coste en un contenedor de 4 núcleos: la DI va a unos 5 s por paso con 2 procesos (unas 7 h para 100 ms);
una corrida pura o híbrida, a unos 2-3 s por paso (3-4 h). Con 4 núcleos caben dos corridas a la vez.
