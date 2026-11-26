# Entrega histórica del modelo mixto DART + CRNN

La combinación elegida usa un único LightGBM DART y la CRNN con contexto nocturno. Para cada etapa calcula `0,70 × log P(DART) + 0,30 × log P(CRNN)` y elige la etapa con mayor puntuación. La predicción corresponde a una noche completa. El HMM pertenecía a los experimentos anteriores.

| Tarea | Criterio de finalización | Estado |
| --- | --- | --- |
| Ordenar los notebooks | Los 21 experimentos anteriores conservan sus salidas en `Notebooks/experiments/`, incluidos diez en `historicos/`. El notebook final se encuentra en la raíz de `Notebooks/`. | Verificado |
| Evaluar la combinación | Las 11 noches de prueba aportaron 15.893 segmentos. La ejecución guardó las métricas por modelo, cohorte y etapa y las tres matrices de confusión. | Verificado |
| Comparar con los controles | Comparar con DART sobre las mismas noches. Para el V6 del compañero usar únicamente las noches de prueba comunes, distinguiendo el V6 de su fusión con DART. | Verificado |
| Entrenar con todos los datos | Se entrenaron ambas ramas con 75.612 segmentos de 34 personas. Se recargaron los pesos y se verificaron 1.196 predicciones sobre un EDF completo. | Verificado |
| Versionar en DVC | Se incorporaron seis archivos bajo `data/models/dart_crnn_mixto/`. Se comprobaron sus hashes y la sincronización con el remoto `r2`. | Publicado en DVC |

## Decisiones de la entrega

- Mantener la primera partición histórica como prueba para poder comparar con V6. Se reservan 7 de 34 personas (20,6 %), con representación de ambas cohortes. Las demás 27 se usan para el entrenamiento de evaluación.
- El resultado histórico de cinco rondas y el resultado de esta reserva 80/20 responden a preguntas distintas. La reserva ya se utilizó durante el desarrollo.
- Mantener separados los artefactos del 80/20 y los ajustados al 100 %. Los pesos definitivos se destinan a una futura integración. El alcance actual cubre investigación, evaluación y exportación.

## Archivos de la entrega histórica

El puntero DVC de esta sección permite recuperar los pesos originales de la entrega de 34 personas. Los ajustes actuales se distribuyen en [modelos/](../modelos/) y `datos/evaluacion_80_20/`.

- [Notebook ejecutado](https://github.com/jcrkboy/micro-proyecto-grupo-7/blob/976523941c351003f186faf0fb68f321ef77a893/Notebooks/dart_crnn_mixto.ipynb) con la preparación de datos, evaluación, matrices, ajuste final e inferencia desde un EDF.
- Manifiesto histórico de la evaluación (`evaluacion_80_20/manifest.json`) con los pesos correspondientes a las 27 personas de entrenamiento. Se recuperaron los pesos de esa partición y se contrastaron con las predicciones históricas antes de guardarlos.
- Manifiesto histórico del modelo definitivo (`final_100/manifest.json`) con los nombres y SHA-256 de los dos modelos, clases, columnas tabulares, rasgos espectrales, contexto, pesos de mezcla y procedencia. DART tardó 467,86 s y la CRNN 37,23 s en ajustarse con los datos preparados.
- [Puntero DVC](https://github.com/jcrkboy/micro-proyecto-grupo-7/blob/976523941c351003f186faf0fb68f321ef77a893/data.dvc) con huella `b3df5052590acf14292f499a0b39631e.dir`. La versión contiene los 188 archivos de datos anteriores y seis archivos nuevos de la entrega. Con esta revisión del puntero, `dvc pull data.dvc` recupera el contenido desde R2.

## Evidencia sobre las mismas personas

| Modelo | Cobertura de prueba | F1 macro | Exactitud | Kappa |
| --- | --- | ---: | ---: | ---: |
| DART mixto | Cinco rondas, 34 personas | 80,10 % | 85,96 % | 0,8074 |
| DART + CRNN 70/30 | Cinco rondas, 34 personas | 81,25 % | 86,80 % | 0,8183 |
| DART mixto | Reserva común, 7 personas | 81,94 % | 87,45 % | 0,8262 |
| V6 del compañero (CRNN + LightGBM + HMM) | Reserva común, 7 personas | 77,49 % | 82,32 % | 0,7536 |
| DART + CRNN 70/30 | Reserva común, 7 personas | 83,48 % | 88,74 % | 0,8435 |
| DART + V6 completo | Reserva común, 7 personas | 83,64 % | 88,93 % | 0,8461 |

La mejora del 70/30 sobre DART en las cinco rondas fue de **1,15 puntos de F1** (IC 95 % de +0,36 a +1,87). En la reserva común de 15.893 segmentos, las diferencias fueron **+1,54** frente a DART (+0,88 a +2,66), **+5,98** frente a V6 (+2,36 a +10,58) y **−0,17** frente a DART + V6 (−1,10 a +0,80). Las diferencias se calculan antes de redondear.

Se remuestrearon personas 5.000 veces dentro de cada cohorte, semilla 42, conservando juntas sus noches y comparando las mismas predicciones de prueba. Los intervalos son orientativos por el número de personas y el uso de estas cohortes durante el desarrollo. La cobertura del V6 completo permite compararlo únicamente en la reserva común. [Comparación histórica con V6](experiments/fusion_dart_v6_companero.ipynb) · [Modelo contextual](experiments/contexto_nocturno_y_fusion_crnn.ipynb)

## Tiempo de inferencia por grabación

Se cronometró la función `predecir_edf` del notebook con el modelo definitivo recargado, en CPU AMD Ryzen 7 5800X. La muestra contiene las 11 grabaciones de la partición de prueba del ajuste 80/20. El cronómetro incluye lectura del EDF local, preparación de ambas entradas, inferencia DART y CRNN y fusión 70/30. Los pesos ya estaban en memoria. La subida HTTP y el arranque del servicio quedan fuera de la medición.

| Cohorte | Grabaciones | Media por grabación |
| --- | ---: | ---: |
| Telemetry | 8 | 17,2 s |
| Cassette | 3 | 35,8 s |
| Ambas | 11 | **22,3 s** |

El tiempo observado fue de 15,3 a 36,6 s por grabación.
