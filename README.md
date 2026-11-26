# Sleep-EDFx Studio · Clasificación automática de estadios del sueño

Sleep-EDFx Studio es la aplicación del proyecto final de la Maestría en Inteligencia Artificial **«Clasificación automática de estadios del sueño mediante aprendizaje de máquina a partir de señales de EEG de polisomnografía»**, propuesto por el Grupo de Ingeniería Biomédica de la Universidad de los Andes. Para apoyar la revisión profesional de un registro EDF, genera un hipnograma preliminar que asigna a cada época de 30 segundos uno de cinco estadios (vigilia, N1, N2, N3 o REM).

El microproyecto de un solo canal EEG fue el antecedente. En el proyecto final, el usuario puede elegir una o ambas derivaciones EEG (Fpz-Cz y Pz-Oz) y añadir, de forma independiente, el movimiento ocular (EOG horizontal) y la actividad muscular del mentón (EMG submental) cuando el registro los contiene.

| Acceso | Ubicación |
|---|---|
| Repositorio | [Código del proyecto en GitHub](https://github.com/jcrkboy/micro-proyecto-grupo-7) |
| Aplicación pública | **POR DEFINIR** |
| Credenciales de la aplicación | Acceso directo, sin cuenta ni contraseña. |

El Grupo 7 está integrado por Juan Carlos Gamboa Peñaranda, Jhoan Sebastián Saavedra Romero, Juan David Rozo Verástegui y Juan Javier Valera Mejías.

## Modelo actual

LightGBM DART clasifica cada época a partir de características tabulares de las señales, mientras que una red convolucional recurrente (CRNN) utiliza la evolución temporal de su espectro. El modelo combina las probabilidades de ambas ramas en escala logarítmica con un peso del 59 % para DART y del 41 % para la CRNN. [Resultados de evaluación, cuadro III del informe (pág. 6)](docs/versionPreFinal/EntregaFinal_v3_20261121/Informe_final_V8.pdf#page=6)

## Despliegue

Necesitas Git, Docker con Compose 2.24 o posterior y acceso a Internet para descargar las imágenes. El script local usa Bash. En Windows, abre **Git Bash** con Docker Desktop en ejecución y configurado para contenedores Linux. En un servidor Linux, usa Docker Engine y Compose. Los contenedores incluyen Python 3.11, FastAPI, LightGBM y TensorFlow para la API, y Angular servido por Nginx para la web.

Clona el repositorio en **el equipo donde correrá Docker**. Git descarga también los tres archivos de `modelos/` que necesita la API.

~~~bash
git clone https://github.com/jcrkboy/micro-proyecto-grupo-7.git
cd micro-proyecto-grupo-7
~~~

### En tu computador

~~~bash
bash apps/deploy/desplegar-local.sh
~~~

El comando construye las imágenes con el código de tu copia, incluidos tus cambios locales. Cuando termine, abre [Sleep-EDFx Studio en localhost](http://127.0.0.1:8081). Para usar otro puerto, ejecuta, por ejemplo, `LOCAL_WEB_PORT=8090 bash apps/deploy/desplegar-local.sh`.

### En un servidor

~~~bash
docker compose -f apps/deploy/docker-compose.yml up -d --pull always --wait
~~~

El comando descarga las imágenes que GitHub Actions publicó en GHCR y espera a que la web pueda consultar la salud de la API. Con la configuración inicial, abre `http://IP_DEL_SERVIDOR` y permite el acceso al puerto 80 en el firewall de la VM. Solo la web publica un puerto. Nginx reenvía las rutas `/api/` al backend.

**El servidor debe tener los pesos en su propio disco.** Por defecto se usa `modelos/` en la raíz del clon. Si están en `/modelos` en la VM, configura `MODELOS_HOST_DIR=/modelos` en `apps/deploy/.env`. La carpeta debe contener `crnn.keras`, `dart.txt` y `manifest.json`. Compose la monta en modo de solo lectura y la API comprueba que los pesos correspondan al manifiesto.

Con los valores predeterminados basta el comando de Compose. Si quieres cambiar el puerto, las imágenes o la ruta de modelos, copia la plantilla a `apps/deploy/.env`, edita sus valores y vuelve a ejecutar el mismo comando. [Plantilla de configuración](apps/deploy/.env.example)

### Configurar, comprobar y actualizar

| Parámetro | Dónde se cambia | Efecto |
|---|---|---|
| `LOCAL_WEB_PORT` | En la terminal al ejecutar el modo local | Puerto de acceso en este equipo. Por defecto, `8081` en `127.0.0.1`. |
| `WEB_HOST_PORT` | `apps/deploy/.env` | Puerto público del servidor. La plantilla usa `80`. |
| `API_IMAGE`, `WEB_IMAGE` | `apps/deploy/.env` | Imágenes del modo servidor. Usa `latest` o una etiqueta publicada `sha-…` de cada servicio para repetir una versión. |
| `MODELOS_HOST_DIR` | `apps/deploy/.env` | Carpeta del anfitrión con los tres archivos. El valor inicial `../../modelos` es relativo a `apps/deploy/`. |
| `SLEEP_API_MAX_UPLOAD_BYTES` | `apps/deploy/.env` | Máximo por EDF en la API. Por defecto son `73400320` bytes (70 MiB). Puedes reducirlo. Para ampliarlo, ajusta también el formulario y el límite de Nginx. |

Comprueba el servicio con `docker compose -f apps/deploy/docker-compose.yml ps`. En local, la [salud de la API](http://127.0.0.1:8081/api/v1/health) debe indicar `model_ready: true`. Para detener ambos servicios y conservar los EDF cargados, ejecuta `docker compose -f apps/deploy/docker-compose.yml stop`.

GitHub Actions publica las imágenes al cambiar los componentes correspondientes en `main`. Para actualizar el servidor, sincroniza el clon con `git pull --ff-only`, espera a que termine la publicación y vuelve a ejecutar el comando de Docker Compose. Si fijaste etiquetas por commit, selecciona las nuevas en el `.env`. [Guía de operación y diagnóstico](apps/deploy/README.md)

## Probar e interpretar un estudio

1. Abre la aplicación, escribe `Prueba 01` como identificador y elige el [EDF sintético de 60 segundos incluido en Git](apps/api/tests/fixtures/sample_eeg_60s.edf).
2. El panel lee la cabecera y muestra los canales antes de subir el archivo. Selecciona al menos un EEG a 100 Hz, **EEG Fpz-Cz** o **EEG Pz-Oz**. Puedes elegir ambos y añadir EOG horizontal a 100 Hz o EMG submental a 1 o 100 Hz si están presentes.
3. Pulsa **Analizar registro**. Con el ejemplo aparecen **2 épocas**. En el resumen verás qué canales se usaron y cuánto tiempo y porcentaje correspondieron a cada estadio.
4. En el hipnograma, el eje horizontal representa el tiempo y el vertical identifica vigilia (W), sueño N1, N2, N3 y REM. Pasa el cursor sobre una época para consultar el estadio y sus probabilidades. Usa **Descargar CSV** para obtener una fila por época o **Descargar JSON** para conservar también los canales, la versión del modelo y el resumen.

Las entradas de los canales desmarcados quedan en cero. El hipnograma y las probabilidades por época sirven de apoyo a la revisión profesional. [Manual de usuario](apoyo/manuales/manual_de_usuario_sleep_edfx_studio.md) · [Contrato de la API y ejemplo con curl](apps/api/README.md)

### Verificar la aplicación

Las pruebas de navegador comprueban que el formulario exige al menos un EEG, que el resumen identifica los canales usados y que el CSV contiene una fila por época. También verifican la leyenda y la consulta de probabilidades en el hipnograma. [Ejecutar las pruebas con Chromium](apps/deploy/README.md#prueba-con-navegador)

## Datos, modelos y análisis

| Carpeta | Contenido |
|---|---|
| [Notebooks/](Notebooks/) | Análisis exploratorio, entrenamiento, comparaciones y evaluación por persona. |
| [modelos/](modelos/) | Los pesos finales de DART y CRNN y su manifiesto, versionados en Git. |
| [datos/](datos/) | Estructura y punteros DVC a las colecciones, características procesadas y ajuste de evaluación 80/20. |
| [apps/](apps/) | Frontend, API y despliegue con Docker Compose. |
| [packages/sleep-staging/](packages/sleep-staging/) | Preprocesamiento, extracción de características e inferencia. |
| [docs/](docs/) y [apoyo/](apoyo/) | Informes, material de presentación, manuales y análisis de apoyo. |

Sleep Telemetry aporta 44 noches de 22 personas y Sleep Cassette aporta 153 noches de 78 personas. Durante el desarrollo, las noches de cada participante quedaron en un mismo grupo. Se utilizaron los registros de 80 personas para entrenar y los de otras 20 para elegir los parámetros y la proporción de la mezcla. [Selección de parámetros del modelo](Notebooks/dart_crnn_mixto.ipynb)

Las etiquetas de entrenamiento proceden de los hipnogramas anotados por expertos. Los estadios 3 y 4 de la anotación original se agrupan en N3. La propuesta también contempla una clase de movimiento (`M`). El modelo clasifica cinco estadios y excluye del entrenamiento las épocas anotadas como movimiento o sin clasificar (`?`). [Correspondencia de etiquetas](packages/sleep-staging/src/sleep_staging/datasets/sleep_edfx.py)

### Reproducir los notebooks

Este entorno es opcional para quienes trabajan con los datos de entrenamiento. Desde la raíz, crea un entorno de Python con `python -m venv .venv`, actívalo e instala `python -m pip install -r requirements.txt`. Para activar el entorno usa `source .venv/bin/activate` en Linux o macOS, `source .venv/Scripts/activate` en Git Bash o `.\.venv\Scripts\Activate.ps1` en PowerShell.

Sustituye los valores de ejemplo por las credenciales de R2 que te facilite el administrador. La opción `--local` las guarda en la configuración privada de DVC.

~~~bash
dvc remote modify --local r2 access_key_id TU_ACCESS_KEY_ID
dvc remote modify --local r2 secret_access_key TU_SECRET_ACCESS_KEY
dvc pull datos/example.edf.dvc
~~~

Esto recupera una noche de ejemplo para la aplicación. Para reproducir los análisis completos, ejecuta `dvc pull` y abre `jupyter lab`. Si regeneras una colección como `datos/processed/`, usa `dvc status` para revisar los cambios, `dvc add datos/processed` para actualizar el puntero y `dvc push` para subir los datos. Registra el puntero actualizado en Git. [Estructura y origen de los datos](datos/README.md) · [EDA de Sleep Telemetry](Notebooks/EDA/EDA_Sleep_EEG_ST7242J0_datset/EDA_Sleep_EEG_dataset.ipynb)
