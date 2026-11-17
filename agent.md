# Guía del repositorio Sleep-EDFx

El proyecto clasifica el sueño por épocas de 30 segundos. Trabaja con el subconjunto Sleep Telemetry de Sleep-EDFx, que reúne 44 noches de 22 sujetos. Cada noche tiene un registro polisomnográfico (PSG) y un hipnograma de referencia. Para preparar el entorno y descargar los datos, sigue el [README principal](README.md).

## Del EDF al hipnograma

En entrenamiento, el paquete Python extrae características del PSG y usa el hipnograma para asignar la etiqueta a cada época. La división se hace por sujeto para que sus dos noches queden en el mismo grupo. En la aplicación, el usuario carga un PSG desde Angular. La API llama al mismo preprocesamiento y al predictor LightGBM, y devuelve las etapas que la interfaz representa en el hipnograma.

## Datos, investigación y materiales

| Carpeta | Qué contiene y cuándo consultarla |
| --- | --- |
| `data/` | Datos gestionados con DVC. `ST-subjects.xls` contiene metadatos de los sujetos, `sleep-telemetry/` contiene los pares de EDF, `processed/` guarda características precalculadas y `models/` aloja artefactos como `sleep_staging_lightgbm_eeg_v2/`, el modelo que consume la API. |
| `.dvc/` | Configuración del remoto R2. Git guarda el puntero `data.dvc` en la raíz. Usa `dvc pull` para recuperar los datos y `dvc remote modify --local` para escribir las credenciales en `.dvc/config.local`. |
| `EDA/` | Análisis exploratorio. `EDA_Sleep_EEG_ST7242J0_individual/` estudia una noche y `EDA_Sleep_EEG_ST7242J0_datset/` recorre las 44. Cada uno tiene su notebook y una carpeta `img/` con figuras. `EDA_Sleep_EEG_ST7242J0/` conserva el informe individual en Markdown con sus gráficos. |
| `Notebooks/` | Experimentos de los integrantes del grupo, búsquedas de hiperparámetros y modelos CNN y CNN-LSTM. `model_jhoan_saavedra_preprocessing_v2.ipynb` exporta el modelo EEG usado por la API. `model_jhoan_saavedra_all_channels.ipynb` evalúa añadir EOG y EMG con el mismo preprocesamiento. |
| `scripts/` | `generate_sample_edf.py` genera un EDF de prueba. `run_lgbm_v2_candidate.py` entrena un candidato LightGBM v2. |
| `matlab/` | Script MATLAB de referencia y figura del EEG con su hipnograma. |
| `docs/` | Presentación e informe del MLOps Stack Canvas y maqueta visual de la aplicación. |
| `manuales/` | Manuales de instalación y de usuario de Sleep-EDFx Studio, y referencia al video de presentación. |

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

En una copia de trabajo también pueden aparecer `.venv/` (entorno Python), `mlruns/` (registros de MLflow), `.pytest_tmp*/` (archivos temporales de pruebas), `.codegraph/` (índice del código) y `.atl/` (registro local de habilidades). En esta copia, `assets/` está vacía.
