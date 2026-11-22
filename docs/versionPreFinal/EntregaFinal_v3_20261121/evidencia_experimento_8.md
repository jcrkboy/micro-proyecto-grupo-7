# Evidencia del experimento 8

El manuscrito de esta entrega es [bare_conf.tex](bare_conf.tex). La numeración V8 identifica la arquitectura DART + CRNN. «Exp. 1» a «Exp. 4» siguen siendo las cuatro variantes internas de V7.

## De dónde sale cada comparación

| Evidencia | Participantes y épocas | Qué permite interpretar |
| --- | --- | --- |
| [Random Forest y LightGBM](../../../Notebooks/experiments/historicos/model_jhoan_saavedra.ipynb), [preprocesamiento EEG v2](../../../Notebooks/experiments/historicos/model_jhoan_saavedra_preprocessing_v2.ipynb) y [canales y cohortes](../../../Notebooks/experiments/model_jhoan_saavedra_all_channels.ipynb) | Reserva de Telemetry de 5 personas y 9.929 épocas. La verificación histórica en Cassette usa otras 3 personas y 8.449 épocas. | El primer cuaderno compara dos clasificadores. El segundo compara los descriptores EEG con su referencia ajustada. El tercero incorpora EOG + EMG y luego evalúa el entrenamiento multicohorte. |
| [CRNN inicial](../../../Notebooks/experiments/historicos/model_cnn_lstm_v3_best.ipynb) | LOSO de 22 personas de Telemetry, 42.467 épocas | La constante `N_SPLITS = 22`, el archivo `resultados_loso_22pacientes_v5.npz` y el soporte total aclaran el rótulo histórico «Mini-LOSO (5 pacientes)». Las predicciones guardadas reproducen exactitud 0.8184, F1 macro 0.7727 y kappa 0.7396. |
| [V5 óptima original](../../../Notebooks/experiments/model_v5_optimo.ipynb) | 20 noches de Cassette, 11 personas, 24.268 épocas | El corte `[40:60]` incluye a SC420 tanto en desarrollo como en evaluación. El 0.7156 de F1 macro procede de este corte. |
| [Reevaluación V4–V7](../../../Notebooks/experiments/DatosV4.ipynb) | 20 noches de Cassette, 10 personas, 24.101 épocas | Este cuaderno excluye SC420 antes de tomar las 20 noches. La V5 óptima obtiene 0.7137. Las últimas salidas, incluidas las de la celda de TTA y las variantes espectrales, sustentan las filas históricas de los cuadros del informe. |
| [Primera fusión de probabilidades](../../../Notebooks/experiments/lightgbm_transiciones_sueno.ipynb) | 34 sujetos, 56 noches y 75.612 épocas, cinco pliegues por sujeto | DART obtuvo 0.8010 de F1 macro y la combinación fija con la CRNN pequeña (75/25) obtuvo 0.8086 sobre las mismas predicciones fuera de muestra. |
| [Selección de V8](../../../Notebooks/dart_crnn_mixto.ipynb) | 80 personas para ajuste y 20 para selección, de ambas cohortes. Las 39 noches de selección contienen 92.369 épocas anotadas. | DART 666 iteraciones, CRNN 27 épocas, mezcla 59/41. El máximo de F1 macro 0.8146 se eligió en estas mismas personas. |
| [Ablación de V8 para este informe](../../../Notebooks/experiments/experimento_8_holdout_datosv4.ipynb) | Las mismas 84 noches de desarrollo y 20 noches de evaluación de la comparación multicohorte corregida | La sección «Métricas del informe e incertidumbre» calcula exactitud, F1 macro, kappa, F1 por estadio e intervalos pareados para los controles. La siguiente genera la matriz de confusión de V8. |
| [Contraste adicional con V6 fase C](../../../Notebooks/experiments/comparacion_dart_crnn_vs_v6_holdout.ipynb) | Otras 19 noches de 10 personas de Cassette, 26.653 épocas | Desarrollo de 84 noches. El mixto alcanzó 0.6855 de F1 macro frente a 0.6432 de V6. Diferencia pareada +0.0423, IC 95 % [+0.0148, +0.0645]. |
| [Exportación final](../../../Notebooks/dart_crnn_mixto_final_100.ipynb) | 100 personas, 197 noches, 457.652 épocas | Ajusta los pesos para inferencia una vez elegida la configuración. |

La documentación histórica de 34 personas y mezcla 70/30 corresponde a una iteración anterior. Las cifras del estudio de 100 personas provienen del notebook mixto actual y de sus manifiestos versionados con DVC.

## Reproducir la comparación principal

1. Recuperar los datos de la revisión del repositorio con `dvc pull data.dvc` si faltan los EDF, los hipnogramas o las recetas guardadas.
2. Ejecutar de principio a fin [experimento_8_holdout_datosv4.ipynb](../../../Notebooks/experiments/experimento_8_holdout_datosv4.ipynb) con el entorno Python del proyecto. El cuaderno usa las configuraciones archivadas y reconstruye las cachés que necesite. Los pesos de la evaluación 80/20 y de `final_100` no intervienen en el ajuste de este experimento.
3. Verificar las 43 personas y 85.796 épocas de desarrollo. La evaluación incluye las dos noches de SC421 a SC430 y comprueba los soportes contra el hipnograma: W 7.393, N1 2.492, N2 9.064, N3 1.600 y REM 3.552.
4. Leer el F1 global sobre las 24.101 épocas agrupadas. El intervalo de cada diferencia usa 5.000 remuestras de personas con semilla 42. Cambiar la semilla del reparto alteraría el grupo de comparación con V4–V7.

La instantánea de entrada de `data.dvc` tiene huella `ae51fd25be9ee4c6595e91d8748983f4.dir`. Los notebooks históricos corresponden a la revisión `9d04da6`.

Los pesos de este ajuste se aprenden en sujetos disjuntos de la reserva. La reserva ya había guiado decisiones en V4–V7. Además, nueve de estos sujetos pertenecieron al entrenamiento histórico del modelo 80/20, SC429 intervino en la selección de su configuración y SC426 participó en el estudio tabular anterior. Por eso el manuscrito presenta una validación retrospectiva; el contraste con V7 usa sus métricas publicadas sobre las mismas épocas.

## Resultado que se llevó al manuscrito

| Modelo en la reserva corregida | Exactitud | F1 macro | Kappa | F1 de N1 |
| --- | ---: | ---: | ---: | ---: |
| V7, Exp. 3 | 0.7971 | 0.7286 | 0.7188 | 0.4144 |
| DART solo | 0.8232 | 0.7765 | 0.7597 | 0.4859 |
| CRNN sola | 0.8120 | 0.7529 | 0.7440 | 0.4579 |
| Mezcla elegida 59/41 | 0.8311 | 0.7791 | 0.7699 | 0.4959 |

La fusión elegida supera al mejor V7 en F1 macro por 5,05 puntos porcentuales en estas noches. Su contraste pareado frente a DART es de +0,25 puntos (IC 95 % de −0,60 a +1,22). La proporción 59/41 se mantuvo tal como se había fijado antes de esta comparación.

## Comparaciones exploratorias conservadas en el cuaderno

El GBDT se entrenó para esta ablación con las mismas filas, etiquetas, 2.280 descriptores y 666 iteraciones que DART. La celda de ajuste cambia el modo de LightGBM a `gbdt` y retira los parámetros de descarte de árboles propios de DART. La mezcla 70/30 aplica un peso de referencia anterior a las probabilidades de esas mismas dos ramas. [Código, resultados e intervalos pareados](../../../Notebooks/experiments/experimento_8_holdout_datosv4.ipynb)

| Variante en la reserva corregida | Exactitud | F1 macro | Kappa | F1 de N1 |
| --- | ---: | ---: | ---: | ---: |
| GBDT de control | 0.8342 | 0.7829 | 0.7719 | 0.4764 |
| Mezcla 70/30 | 0.8321 | 0.7817 | 0.7714 | 0.4995 |

En estas noches ambas variantes alcanzaron un F1 macro superior al 0.7791 de la configuración predefinida. La diferencia pareada de la fusión 59/41 frente a GBDT fue de −0,38 puntos porcentuales (IC 95 % de −1,17 a +0,37).
