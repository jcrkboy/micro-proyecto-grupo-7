# Sleep-EDFx Studio · Grupo 7

Sleep-EDFx Studio convierte un registro de sueño en formato EDF en un hipnograma preliminar. El usuario elige los canales de la polisomnografía y el modelo estima un estadio por cada 30 segundos de señal. El resultado permite explorar la noche, consultar la confianza de cada predicción y exportar los datos para revisión profesional.

| Acceso | Ubicación |
|---|---|
| Repositorio | [GitHub · micro-proyecto-grupo-7](https://github.com/jcrkboy/micro-proyecto-grupo-7) |
| Aplicación pública | **POR DEFINIR** |
| Demostración | [Video de presentación del proyecto](https://drive.google.com/file/d/1NIcqw7noABbsWgwwZVIIpzwrwPM_Cwm5/view) |
| Credenciales de la aplicación | Acceso directo, sin cuenta ni contraseña. |

El Grupo 7 está integrado por Juan Carlos Gamboa Peñaranda, Jhoan Sebastián Saavedra Romero, Juan David Rozo Verástegui y Juan Javier Valera Mejías.

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

El resultado es preliminar y requiere revisión profesional. El modelo combina DART (59 %) y una red CRNN (41 %). Las entradas de los canales desmarcados quedan en cero. [Manual de usuario](apoyo/manuales/manual_de_usuario_sleep_edfx_studio.md) · [Contrato de la API y ejemplo con curl](apps/api/README.md)

## Cómo verificar la entrega

| Criterio de la rúbrica | Comprobación reproducible |
|---|---|
| Funcionamiento (35 %) | Carga el EDF de ejemplo, elige un EEG y comprueba que aparecen dos épocas y que el CSV contiene dos filas de datos. [Prueba de despliegue con Playwright](apps/web/e2e/despliegue.spec.ts) |
| Documentación del despliegue (15 %) | Sigue uno de los dos procedimientos desde un clon nuevo y consulta la salud de la API. La dirección pública se completará al desplegar la VM. |
| Parametrización (15 %) | Arranca en otro puerto con `LOCAL_WEB_PORT=8090` o cambia un valor del servidor en el archivo de entorno y vuelve a desplegar. [Plantilla con valores iniciales](apps/deploy/.env.example) |
| Usabilidad y presentación (35 %) | Comprueba que el formulario impide analizar sin EEG, que la leyenda permite identificar los cinco estadios y que el cursor muestra la confianza por época. [Prueba de interacción del hipnograma](apps/web/e2e/hypnogram.spec.ts) |

La [guía de pruebas en Chromium](apps/deploy/README.md#prueba-con-navegador) incluye el comando para repetir las verificaciones de interfaz.

## Datos, modelos y análisis

| Carpeta | Contenido |
|---|---|
| [Notebooks/](Notebooks/) | Análisis exploratorio, entrenamiento, comparaciones y evaluación por persona. |
| [modelos/](modelos/) | Los pesos finales de DART y CRNN y su manifiesto, versionados en Git. |
| [datos/](datos/) | Estructura y punteros DVC a las colecciones, características procesadas y ajuste de evaluación 80/20. |
| [apps/](apps/) | Frontend, API y despliegue con Docker Compose. |
| [packages/sleep-staging/](packages/sleep-staging/) | Preprocesamiento, extracción de características e inferencia. |
| [docs/](docs/) y [apoyo/](apoyo/) | Informes, material de presentación, manuales y análisis de apoyo. |

Sleep Telemetry aporta 44 noches de 22 personas y Sleep Cassette aporta 153 noches de 78 personas. La evaluación separa a las personas entre entrenamiento (80 personas, 158 noches) y prueba (20 personas, 39 noches). El ajuste final distribuido con la aplicación utiliza las 100 personas. [Evaluación por persona](Notebooks/dart_crnn_mixto.ipynb) · [Entrenamiento final](Notebooks/dart_crnn_mixto_final_100.ipynb)

### Reproducir los notebooks

Este entorno es opcional para quienes trabajan con los datos de entrenamiento. Desde la raíz, crea un entorno de Python con `python -m venv .venv`, actívalo e instala `python -m pip install -r requirements.txt`. Para activar el entorno usa `source .venv/bin/activate` en Linux o macOS, `source .venv/Scripts/activate` en Git Bash o `.\.venv\Scripts\Activate.ps1` en PowerShell.

Sustituye los valores de ejemplo por las credenciales de R2 que te facilite el administrador. La opción `--local` las guarda en la configuración privada de DVC.

~~~bash
dvc remote modify --local r2 access_key_id TU_ACCESS_KEY_ID
dvc remote modify --local r2 secret_access_key TU_SECRET_ACCESS_KEY
dvc pull datos/example.edf.dvc
~~~

Esto recupera una noche de ejemplo para la aplicación. Para reproducir los análisis completos, ejecuta `dvc pull` y abre `jupyter lab`. Si regeneras una colección como `datos/processed/`, usa `dvc status` para revisar los cambios, `dvc add datos/processed` para actualizar el puntero y `dvc push` para subir los datos. Registra el puntero actualizado en Git. [Estructura y origen de los datos](datos/README.md) · [EDA de Sleep Telemetry](Notebooks/EDA/EDA_Sleep_EEG_ST7242J0_datset/EDA_Sleep_EEG_dataset.ipynb)
