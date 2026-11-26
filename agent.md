# Guía del repositorio Sleep-EDFx

El proyecto clasifica el sueño por épocas de 30 segundos. La entrega final usa 44 noches de Sleep Telemetry y 153 de Sleep Cassette, correspondientes a 100 personas. Cada noche utilizable tiene un registro polisomnográfico (PSG) y un hipnograma de referencia. Para preparar el entorno y descargar los datos, sigue el [README principal](README.md).

## Del EDF al hipnograma

En entrenamiento, el paquete Python extrae características del PSG y usa el hipnograma para asignar la etiqueta a cada época. La división se hace por sujeto para que sus dos noches queden en el mismo grupo. En la aplicación, el usuario carga un PSG desde Angular. La API llama al mismo preprocesamiento y al predictor DART + CRNN, y devuelve las etapas que la interfaz representa en el hipnograma.

## Datos, investigación y materiales

| Carpeta | Qué contiene y cuándo consultarla |
| --- | --- |
| `datos/` | Datos gestionados con DVC. Contiene los metadatos de los sujetos, los EDF, los hipnogramas y las características precalculadas. |
| `modelos/` | La API carga `dart.txt`, `crnn.keras` y `manifest.json` desde esta carpeta de Git. |
| `.dvc/` | Configuración del remoto R2. Git guarda los punteros `.dvc` en `datos/`. Usa `dvc pull` para recuperar los datos y `dvc remote modify --local` para escribir las credenciales en `.dvc/config.local`. |
| `Notebooks/EDA/` | Análisis exploratorio. `EDA_Sleep_EEG_ST7242J0_individual/` estudia una noche y `EDA_Sleep_EEG_ST7242J0_datset/` recorre las 44. Cada uno tiene su notebook y una carpeta `img/` con figuras. `EDA_Sleep_EEG_ST7242J0/` conserva el informe individual en Markdown con sus gráficos. |
| `datos/sleep-cassette/` y `datos/referencias/` | EDF de la entrega parcial de Cassette y predicciones por época de la CRNN de Telemetry. El adaptador de Cassette empareja por sujeto y noche. |
| `Notebooks/` | Evaluación por persona y entrenamiento final de la combinación de DART y CRNN en Telemetry y Cassette. [Notebook principal](Notebooks/dart_crnn_mixto.ipynb) · [Registro de experimentos](Notebooks/agent.md) |
| `Notebooks/experiments/` | `model_jhoan_saavedra_all_channels.ipynb` entrena los controles LightGBM. `model_v6.ipynb` conserva la arquitectura y los resultados originales del compañero. La carpeta también contiene las comparaciones y búsquedas posteriores. |
| `Notebooks/experiments/historicos/` | Modelos previos y búsquedas de hiperparámetros. `model_jhoan_saavedra_preprocessing_v2.ipynb` exporta un modelo EEG de una etapa anterior. |
| `scripts/` | `generate_sample_edf.py` genera un EDF de prueba. `run_lgbm_v2_candidate.py` entrena un candidato LightGBM v2. |
| `apoyo/matlab/` | Script MATLAB de referencia y figura del EEG con su hipnograma. |
| `docs/` | Presentación e informe del MLOps Stack Canvas y maqueta visual de la aplicación. |
| `apoyo/manuales/` | Manuales de instalación y de usuario de Sleep-EDFx Studio, y referencia al video de presentación. |

## Comparación con el experimento del compañero

El cuaderno V4 de Colab extrae representaciones de 64 variables con tres ramas Conv1D (EEG, EOG y EMG), atención y una BiLSTM. LightGBM clasifica estas representaciones. La ventana temporal es de 15 épocas. La celda de entrenamiento tabular de V4 calcula una exactitud cercana a 0,95 sobre las propias filas de ajuste. La evaluación histórica de Cassette usa otras 20 noches, seleccionadas por posición en la lista de registros. Sobre sus 24.268 épocas, la CRNN pura alcanza F1 macro de 0,6114 y el híbrido entrenado con ambas cohortes alcanza 0,6853.

En los notebooks V5 y V6, el nombre interno de la red es V7. En la misma evaluación de 20 noches, el híbrido de V5 obtiene 0,7126 de F1 macro y V5 óptimo obtiene 0,7156. V6 concatena las representaciones de tres épocas adyacentes (192 variables) y usa las probabilidades de LightGBM con una decodificación de Viterbi por noche. Esa fase obtiene 0,7164 de F1 macro, 0,7910 de exactitud y 0,7093 de kappa. V6 con aumentos en inferencia obtiene 0,7160 de F1 macro. La variante `model_v6_3Improv.ipynb` comparte esos resultados. La selección se hizo por F1 macro en las 24.268 épocas reservadas. En estos notebooks, la optimización tabular usa representaciones de un extractor ajustado con todo el conjunto de entrenamiento. Para comparar con otros modelos conviene usar la evaluación externa.

El corte histórico reserva las noches 41 a 60 en orden de archivo. Sus 20 noches pertenecen a 11 sujetos y SC420 también tiene una noche entre las primeras 40 usadas para entrenar. Se reconstruyó la partición con el catálogo de MNE y las anotaciones de Sleep-EDFx 1.0.0. Coinciden las 85.796 épocas de ajuste y el soporte de los cinco estadios en la evaluación. [Base de datos Sleep-EDFx](https://physionet.org/content/sleep-edfx/1.0.0/)

| Validación | Épocas | F1 macro de LightGBM entrenado con Telemetry | F1 macro de LightGBM mixto | F1 macro de la CRNN pura |
| --- | ---: | ---: | ---: | ---: |
| Telemetry, 5 sujetos y vigilia completa | 9.929 | 0,7938 | 0,7940 | — |
| Cassette, 3 sujetos y vigilia completa | 8.449 | 0,3438 | 0,7672 | — |
| Telemetry, mismas épocas tras el recorte de vigilia del compañero | 9.883 | 0,7927 | 0,7928 | 0,7219 |

El modelo mixto se ajustó con 57.234 épocas de 17 sujetos de Telemetry y 9 de Cassette. La validación reservó a `SC406`, `SC457` y `SC472` en Cassette. Allí solo los dos EEG y el EOG comparten los 100 Hz de Telemetry. Las columnas derivadas del EMG de alta frecuencia se marcan como ausentes para Cassette. El modelo experimental se recupera mediante DVC en `datos/experimentos/lightgbm_st_sc/`, con el archivo de pesos y el esquema de ambas cohortes.

### Comparación directa con el híbrido V6

El cruce excluye a SC406, presente en el entrenamiento de V6. Se aplicó el mismo recorte de vigilia a ambos modelos y se comprobó la etiqueta de cada época. Con los pesos guardados, se obtienen estos F1 macro.

| Noche de Cassette | Épocas | LightGBM mixto | V6 contextual + HMM |
| --- | ---: | ---: | ---: |
| SC4572 | 1.095 | 0,4541 | 0,2245 |
| SC4722 | 1.130 | 0,5678 | 0,5822 |
| Ambas noches | 2.225 | 0,5396 | 0,4390 |

Para reproducir el cruce desde la raíz, ejecuta `python scripts/compare_cassette_hybrid.py` después de instalar las dependencias y recuperar los datos con DVC. `datos/referencias/hibrido_v6/` contiene la red, el clasificador contextual y las probabilidades iniciales y de transición del HMM. Se conservaron los pesos de Keras y se omitió un campo de cuantización nulo para compatibilidad. El clasificador contextual se guardó en formato de texto nativo de LightGBM.

## Paquete Python compartido

La biblioteca está en `packages/sleep-staging/`. Su instalación y dependencias opcionales se declaran en `pyproject.toml`. El código importable está en `src/sleep_staging/`. Consulta el [README del paquete](packages/sleep-staging/README.md).

| Subcarpeta del paquete | Responsabilidad |
| --- | --- |
| `src/sleep_staging/config/` | Parámetros del preprocesamiento, incluidos canales, duración de época y ventanas temporales. |
| `src/sleep_staging/io/` | Lectura de EDF y filtrado de señales. |
| `src/sleep_staging/datasets/` | Identificación de registros y anotaciones de Sleep-EDFx. |
| `src/sleep_staging/preprocessing/` | `PreprocessingPipeline` coordina segmentación en épocas, extracción de características, normalización por registro y contexto temporal. |
| `src/sleep_staging/training/` | Construcción y caché del conjunto supervisado, división por sujeto, entrenamiento, búsqueda de hiperparámetros y evaluación. |
| `src/sleep_staging/inference/` | Carga del modelo y de su manifiesto. `SleepStagePredictor` comprueba las características esperadas y predice una etapa por época. |
| `tests/` | Pruebas de segmentación, preprocesamiento, artefactos y entrenamiento. Aquí se comprueba que añadir o reordenar canales conserve las características EEG. |

## Aplicaciones y despliegue

| Carpeta | Qué contiene |
| --- | --- |
| `apps/api/` | Backend FastAPI. La aplicación se crea en `src/sleep_api/main.py`. Incluye un Dockerfile, una plantilla de configuración y el lanzador `run.sh`. Consulta el [README del backend](apps/api/README.md). |
| `apps/api/src/sleep_api/` | `api/routes/` expone salud, carga de EDF y predicción. `schemas/` define los contratos HTTP, `services/` coordina la inferencia, `infrastructure/` gestiona los archivos cargados y `core/` reúne configuración y excepciones. |
| `apps/api/storage/uploads/` | Directorio de trabajo para los EDF recibidos por la API. |
| `apps/api/tests/` | Pruebas de los endpoints y de inferencia con el modelo real. `fixtures/` contiene un EDF de 60 segundos. |
| `apps/web/` | Frontend Angular. `src/` contiene el punto de entrada, los estilos y la aplicación. `src/environments/` configura cada entorno, `public/` contiene recursos estáticos, `e2e/` prueba el flujo del hipnograma y `.vscode/` guarda ajustes del editor. |
| `apps/web/src/app/components/` | `upload-form/` permite cargar un EDF, `analysis-modal/` presenta el análisis, `hypnogram/` dibuja las etapas y `sleep-summary/` muestra el resumen. |
| `apps/web/src/app/core/` | `models/` define tipos, `services/` conecta la interfaz con la API y `utils/` reúne funciones para el hipnograma y la exportación de resultados. |
| `apps/deploy/` | Docker Compose y configuración para ejecutar las imágenes de la API y la web en una VM. Consulta la [guía de despliegue](apps/deploy/README.md). |
| `.github/workflows/` | Flujos de GitHub Actions que construyen y publican las imágenes de la API y de la web en GitHub Container Registry. |

## Carpetas locales

En una copia de trabajo también pueden aparecer `.venv/` (entorno Python), `apoyo/mlruns/` (registros de MLflow), `.pytest_tmp*/` (archivos temporales de pruebas), `.codegraph/` (índice del código) y `.atl/` (registro local de habilidades).
