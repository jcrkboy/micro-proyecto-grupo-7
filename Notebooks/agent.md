# Experimentos de clasificación de etapas de sueño

El [notebook principal](dart_crnn_mixto.ipynb) usa **70 % DART y 30 % CRNN contextual** en escala logarítmica, sin HMM. Esta combinación obtuvo **81,25 % de F1 macro** en las cinco rondas y **83,48 %** en la reserva del notebook de entrega. El ajuste final usa los 34 participantes y guarda los dos modelos en `data/models/dart_crnn_mixto/`. [Comparación pareada y tareas de la entrega](TASK.md)

Los experimentos anteriores y sus salidas están en [experiments/](experiments/). Los primeros modelos de Colab y los cuadernos de la API se conservan en [experiments/historicos/](experiments/historicos/).

**Resultado al 18 de noviembre de 2026.** La mejor configuración fija observada en las cinco rondas alcanzó **81,33 % de F1 macro, 87,06 % de exactitud y kappa 0,8212**, con un solo DART y una CRNN contextual con HMM. La nueva regla de selección interna obtuvo **81,24 %**, frente a **81,01 %** de la regla anterior. El **83,64 %** de DART + V6 completo corresponde a las 11 noches de la primera ronda. [Comparación global y por cohorte](experiments/contexto_nocturno_y_fusion_crnn.ipynb)

## Cómo comparar los resultados

La métrica principal es el F1 macro de cinco etapas (W, N1, N2, N3 y REM). Para el resultado global se reúnen las predicciones de prueba de las cinco rondas y se calcula el F1 sobre esas predicciones. Cada persona aparece en prueba una sola vez, con todas sus noches. La exactitud y el kappa de Cohen acompañan al F1. Estas rondas ya han orientado decisiones de desarrollo, por lo que una validación externa aportaría evidencia independiente.

| Datos con etiquetas de referencia | Personas | Noches | Segmentos de 30 s |
| --- | ---: | ---: | ---: |
| Sleep-Telemetry | 22 | 44 | 42.691 |
| Sleep-Cassette disponible con PSG e hipnograma emparejados | 12 | 12 | 32.921 |
| Ambas cohortes | 34 | 56 | 75.612 |

La primera ronda entrenó con 27 personas, 45 noches y 59.719 segmentos. Se reservó la totalidad de las noches de otras siete personas (ocho noches de Telemetry y tres de Cassette, 15.893 segmentos). El otro reparto frecuente en estos notebooks es un conjunto de desarrollo de 26 personas y una reserva de ocho. Identificar el reparto antes de citar una cifra.

## Experimentos y resultados de referencia

| Comparación | F1 macro | Dónde comprobarla |
| --- | ---: | --- |
| DART mixto, cinco rondas | 80,10 % | [Predicciones y matrices](experiments/resumen_lightgbm_crnn.ipynb) |
| DART + CRNN pequeña, cinco rondas | 80,86 % | [Fusión y tiempos](experiments/resumen_lightgbm_crnn.ipynb) |
| DART + CRNN residual / multiescala, cinco rondas | 80,87 % / 80,83 % | [Refinamiento](experiments/refinamiento_crnn_pequena.ipynb) |
| DART + V6 compacto con HMM / sin HMM, cinco rondas | **80,96 %** / 80,69 % | [Ablación del HMM](experiments/fusion_dart_v6_compacto.ipynb) |
| DART solo / DART + CRNN pequeña, primera ronda | 81,94 % / 82,74 % | [Resumen](experiments/resumen_lightgbm_crnn.ipynb) |
| V6 completo con Viterbi / DART + V6 con probabilidades del HMM, primera ronda | 77,49 % / **83,64 %** | [Fusión con V6](experiments/fusion_dart_v6_companero.ipynb) |
| DART / GBDT ajustado, reserva histórica de ocho personas | 79,81 % / 79,68 % | [Búsqueda tabular](experiments/busqueda_hiperparametros_lightgbm_mixto.ipynb) |

Entre las primeras redes pequeñas, la original fue la referencia práctica (86,69 % de exactitud, kappa 0,8171). La mejora de F1 de la residual fue inferior a 0,01 puntos porcentuales y el ajuste de su red tomó unos 26 s frente a 14 s en la primera ronda. En el V6 completo, la mezcla con DART alcanzó 88,93 % de exactitud y kappa 0,8461 en la primera ronda. La mejora respecto a DART fue de 1,70 puntos de F1 en esas mismas noches. El V6 completo terminó una de cinco rondas. [Comparación justa y tiempos](experiments/comparacion_justa_lightgbm_v6.ipynb)

## Cómo se entrenaron

**DART mixto.** LightGBM multiclase sobre 2.280 características tabulares con contexto temporal. Usa 667 iteraciones, tasa de aprendizaje 0,03, profundidad 8, 36 hojas, mínimo 25 ejemplos por hoja, fracción de columnas 0,60 y fracción de filas 0,80 en cada iteración. Regularización L1 0,1 y L2 1,5, `drop_rate=0.1`, `skip_drop=0.5` y semilla 42. Los pesos de clase son N1 2,20, N2 0,41, N3 1,56, REM 1,00 y W 2,01. [Configuración completa y orden de las clases](../data/experimentos/lightgbm_st_sc/experimento.json) · [Notebook de Jhoan](experiments/model_jhoan_saavedra_all_channels.ipynb)

**CRNN pequeña original.** Usa las características del segmento actual escaladas con los percentiles 10 y 90 del entrenamiento, con indicador de ausencia del EMG. Lee ventanas de 64 segmentos con paso 32. Aplica Conv1D de 48 filtros y ancho 3 con ReLU, dropout 0,15, GRU bidireccional de 32 unidades por dirección, dropout 0,20 y softmax de cinco clases. Usa Adam a 0,001, lote 32, 12 épocas, ponderación inversa por frecuencia con exponente 0,35 y semilla 42. Se promedian las probabilidades en ventanas solapadas. La fusión por etapa es `0,75 × P(DART) + 0,25 × P(CRNN)`. La residual añade una convolución dilatada, normalización y GRU de 48 unidades por dirección. Entrena 12 épocas a 0,001 y ocho a 0,00035. [Redes y validación](experiments/refinamiento_crnn_pequena.ipynb)

**V6 completo del compañero.** La CRNN procesa secuencias de 15 segmentos de señal, produce 64 características por segmento y concatena tres segmentos vecinos para el cabezal LightGBM de 192 entradas. El cabezal GBDT usa 600 iteraciones, tasa 0,0644405, 62 hojas, profundidad 7, mínimo 130 ejemplos por hoja, fracción de columnas 0,583576 y pesos de clase equilibrados. El HMM aprende transiciones del entrenamiento. Para combinarlo con DART se toman las probabilidades marginales por etapa del HMM, con peso 0,25. La CRNN completa tardó unas cinco horas en la primera ronda. [Arquitectura original](experiments/model_v6.ipynb) · [Reentrenamiento sobre sujetos comunes](experiments/comparacion_justa_lightgbm_v6.ipynb)

## Reproducción

Desde la raíz, `dvc pull` recupera los datos que referencia `data.dvc`. Las señales de V6 y los modelos por ronda también usan cachés locales. [Comparación justa](experiments/comparacion_justa_lightgbm_v6.ipynb) prepara las señales en `.sleep-cv/8f83a22b1d3a65d3/` y mide el ajuste DART de la primera ronda. [Validación de la fusión](experiments/lightgbm_transiciones_sueno.ipynb) genera los controles y los modelos DART de las otras rondas en `.sleep-cv/fusion-crnn/663d52206f296fcc/`. Los checkpoints son específicos de su partición. Los notebooks de informes conservan sus salidas. Al reejecutar, las cachés históricas comprueban código, versiones y entradas. Algunos experimentos incluyeron el puntero completo `data.dvc` en su huella. Una revisión posterior de ese puntero puede requerir regenerar la caché incluso cuando el cambio solo añade un modelo entrenado.

## Experimento con presupuesto de 20 minutos

La [fusión DART + V6 compacto](experiments/fusion_dart_v6_compacto.ipynb) conserva la señal normalizada de V6, el contexto anterior/actual/siguiente, el cabezal LightGBM y el HMM. Resume cada 5 s en seis bandas por canal. La nueva CRNN tiene Conv1D de 32 filtros y ancho 3, una capa densa de 32 y una GRU bidireccional de 16 unidades por dirección sobre bloques de 15 épocas. Usa dropout 0,15/0,20, Adam a 0,001, 12 épocas, lote 64, exponente de clase 0,35 y semilla 42. El cabezal recibe 96 características, usa 180 iteraciones, 31 hojas, profundidad 7, tasa 0,06, mínimo 80 ejemplos por hoja, fracción de columnas 0,8, L2 1,5 y clases equilibradas. La comparación principal fija 75 % DART y 25 % de probabilidades marginales del compacto con HMM. Una segunda combinación mide qué pasa al omitir el HMM. [Implementación y cronómetros](../scripts/evaluar_v6_compacto.py)

Las cinco rondas terminaron. En la primera, la rama compacta tardó 15,03 s en CPU, incluidos el entrenamiento de la CRNN, la extracción de representaciones de entrenamiento y el ajuste del cabezal y el HMM. Sumados a los 420,66 s medidos previamente para DART, el ajuste en serie habría tomado 7 min 16 s con entradas preparadas. La preparación espectral de las 56 noches desde señales V6 ya filtradas tomó unos 9 s en la ejecución inicial. El notebook separa la inferencia de la rama compacta sobre las noches de prueba. Los pesos de la red, el cabezal, el HMM, los tiempos y las predicciones por ronda se guardan localmente en `.sleep-cv/v6-compacto/`.

## Ablación del segundo LightGBM

La sección «Un solo LightGBM» del [notebook de fusión](experiments/fusion_dart_v6_compacto.ipynb) reutiliza los pesos por ronda y conecta la salida softmax de la CRNN directamente al HMM. Se conserva la mezcla externa 75 % DART y 25 % de la rama CRNN con HMM. Con la CRNN compacta, el F1 macro global es **80,75 %**, la exactitud **86,70 %** y el kappa **0,8163**. Eliminar el segundo LightGBM redujo el F1 en 0,21 puntos frente al compacto con cabezal. En la primera ronda, el ajuste de DART, la CRNN compacta y las transiciones suma aproximadamente **7 min 10 s** desde entradas preparadas.

Con la CRNN original del compañero y el mismo HMM, la fusión directa alcanzó **82,80 %** de F1 en la primera ronda. La variante con el LightGBM interno había alcanzado **83,64 %** en esas mismas 11 noches. Las cinco horas corresponden al entrenamiento del extractor original. Esta ablación usó sus pesos ya guardados.

## Tamaño de CRNN y porcentaje de mezcla

La [búsqueda de mezclas](experiments/busqueda_mezclas_dart_crnn_hmm.ipynb) compara cuatro tamaños de la rama directa. Las ternas (filtros convolucionales, unidades densas, unidades GRU por dirección) son mini (16, 16, 8), compacta (32, 32, 16), mediana (48, 48, 32) y amplia (64, 64, 48). La cuadrícula incluye 0, 25, 40, 50, 60, 65, 70, 75, 80, 85, 90 y 100 % de DART. Todas las redes usan los mismos sujetos y orden de minibatches dentro de cada ajuste, con semilla 42. El HMM se estima en el entrenamiento de cada partición.

En cada ronda externa, otra ronda independiente del grupo de prueba permite elegir el tamaño y el peso. DART también se vuelve a entrenar para esta validación interna. La fila «Selección interna» del notebook reúne 75.612 predicciones externas siguiendo esa regla. La tabla de mezclas fijas permite consultar comparaciones como 70/30 frente a 75/25. Los modelos de las cinco rondas, las probabilidades, el inventario de personas y los tiempos quedan en la caché local `.sleep-cv/busqueda-fusion-directa/`. [Implementación de la búsqueda](../scripts/buscar_fusion_crnn.py) · [Ajuste interno de DART](../scripts/dart_interno_fusion.py)


La selección interna logró **81,01 % de F1 macro global**, **86,81 % de exactitud** y **kappa 0,8177**. Eligió amplia 70/30, amplia 75/25, mediana 70/30, mediana 75/25 y amplia 65/35 en las rondas 1–5 respectivamente. En Telemetry el F1 fue 80,17 % y en Cassette 77,12 %. El mayor valor exploratorio para una configuración fija de esta búsqueda fue **80,91 % de F1 con 75 % DART y 25 % CRNN amplia + HMM**. La misma red con 70/30 obtuvo 80,87 %. La amplia tiene 62.629 parámetros y sus ajustes externos duraron 25–38 s en CPU. Sumando el DART previamente cronometrado y la CRNN amplia de la primera ronda, el ajuste en serie se estima en 7 min 38 s desde entradas preparadas.

## Contexto nocturno y fusión geométrica

El [notebook de contexto nocturno](experiments/contexto_nocturno_y_fusion_crnn.ipynb) compara dos iteraciones con las mismas 34 personas y cinco rondas. La nueva CRNN combina seis bandas de cada canal en subventanas de 5 s, normalización robusta por noche y dos medias espectrales de contexto de 7,5 y 2 min. Tiene 48 filtros Conv1D de ancho 3, 48 unidades densas, GRU bidireccional de 32 por dirección y 43.813 parámetros. Adam 0,001, 15 épocas, lote 64, dropout 0,15/0,20, exponente de clase 0,35, semilla 42. El entrenamiento alterna desfases 0, 5 y 10 en bloques de 15 segmentos. Se agregan las tres vistas en log-probabilidad y se calcula el posterior del HMM por noche. [Implementación](../scripts/crnn_contexto_nocturno.py)

La mejor fórmula fija puntúa cada etapa con 0,70 × log P(DART) + 0,15 × log P(CRNN) + 0,15 × log P(CRNN tras HMM). Con una configuración por cohorte elegida internamente se obtuvo 81,31 % global en el análisis exploratorio, con mayor F1 en Cassette y menor en Telemetry que la fórmula fija. El ajuste CRNN/HMM tardó 29–31 s por ronda. Las probabilidades, tiempos y pesos están en el subdirectorio local `contexto-nocturno` de la caché de búsqueda de fusión directa.
