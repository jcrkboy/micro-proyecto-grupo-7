# Sleep-EDFx Studio · Clasificación automática de estadios del sueño

Sleep-EDFx Studio es la aplicación del proyecto final de la Maestría en Inteligencia Artificial **«Clasificación automática de estadios del sueño mediante aprendizaje de máquina a partir de señales de EEG de polisomnografía»**, propuesto por el Grupo de Ingeniería Biomédica de la Universidad de los Andes. Para apoyar la revisión profesional de un registro EDF, genera un hipnograma preliminar que asigna a cada época de 30 segundos uno de cinco estadios (vigilia, N1, N2, N3 o REM).

El microproyecto de un solo canal EEG fue el antecedente. En el proyecto final, el usuario puede elegir una o ambas derivaciones EEG (Fpz-Cz y Pz-Oz) y añadir, de forma independiente, el movimiento ocular (EOG horizontal) y la actividad muscular del mentón (EMG submental) cuando el registro los contiene.

| Acceso | Ubicación |
|---|---|
| Repositorio | [Código del proyecto en GitHub](https://github.com/jcrkboy/micro-proyecto-grupo-7) |
| Aplicación pública | [Abrir Sleep-EDFx Studio en Fly.io](https://sleepedfx.fly.dev/) |
| Credenciales de la aplicación | Acceso directo, sin cuenta ni contraseña. |

El Grupo 7 está integrado por Juan Carlos Gamboa Peñaranda, Jhoan Sebastián Saavedra Romero, Juan David Rozo Verástegui y Juan Javier Valera Mejías.

## Modelo actual

LightGBM DART clasifica cada época a partir de características tabulares de las señales, mientras que una red convolucional recurrente (CRNN) utiliza la evolución temporal de su espectro. El modelo combina las probabilidades de ambas ramas en escala logarítmica con un peso del 59 % para DART y del 41 % para la CRNN. [Resultados de evaluación, cuadro III del informe (pág. 6)](docs/versionPreFinal/EntregaFinal_v3_20261121/Informe_final_V8.pdf#page=6)

## Despliegue

Necesitas Git, Docker con Compose 2.24 o posterior y acceso a Internet para la primera instalación. En macOS y Windows, inicia Docker Desktop (en Windows, usa contenedores Linux). En Linux puedes usar Docker Engine con el complemento Compose. Los contenedores incluyen Python 3.11, FastAPI, LightGBM y TensorFlow para la API, y Angular servido por Nginx para la web.

Clona el repositorio en **el equipo donde correrá Docker**. Git incluye los tres archivos de `modelos/` que necesita la API y un EDF sintético para probarla. Si vas a trabajar con las colecciones de estudio o a reproducir los notebooks, sigue la [guía de descarga con DVC](#descargar-los-datos-con-dvc).

~~~text
git clone https://github.com/jcrkboy/micro-proyecto-grupo-7.git
cd micro-proyecto-grupo-7
~~~

### En tu computador

**Con Docker, sin Bash.** Usa la terminal de Linux o macOS, o PowerShell en Windows. Desde el editor, crea el archivo `apps/deploy/.env` con estas tres líneas. Si ya existe, actualiza solo esas entradas.

~~~dotenv
API_IMAGE=sleep-edfx-api:local
WEB_IMAGE=sleep-edfx-web:local
WEB_HOST_PORT=127.0.0.1:8081
~~~

Desde la raíz del repositorio, construye las imágenes e inicia la aplicación. Los comandos son los mismos en las tres plataformas.

~~~text
docker build -t sleep-edfx-api:local -f apps/api/Dockerfile .
docker build -t sleep-edfx-web:local apps/web
docker compose -f apps/deploy/docker-compose.yml up -d --pull never --wait
~~~

Abre [Sleep-EDFx Studio en tu navegador](http://127.0.0.1:8081). En los siguientes arranques basta con la última línea. Si cambias el código, vuelve a construir la imagen del componente que modificaste.

**Con el script Bash.** En Linux, macOS o Git Bash para Windows, este comando automatiza la construcción y el arranque con el mismo puerto local.

~~~bash
bash apps/deploy/desplegar-local.sh
~~~

Para usar otro puerto con el script, ejecuta, por ejemplo, `LOCAL_WEB_PORT=8090 bash apps/deploy/desplegar-local.sh`.

### En un servidor

~~~bash
docker compose -f apps/deploy/docker-compose.yml up -d --pull always --wait
~~~

El comando descarga las imágenes que GitHub Actions publicó en GHCR y espera a que la web pueda consultar la salud de la API. Con la configuración inicial, abre `http://IP_DEL_SERVIDOR` y permite el acceso al puerto 80 en el firewall de la VM. Solo la web publica un puerto. Nginx reenvía las rutas `/api/` al backend.

**El servidor debe tener los pesos en su propio disco.** Por defecto se usa `modelos/` en la raíz del clon. Si están en `/modelos` en la VM, configura `MODELOS_HOST_DIR=/modelos` en `apps/deploy/.env`. La carpeta debe contener `crnn.keras`, `dart.txt` y `manifest.json`. Compose la monta en modo de solo lectura y la API comprueba que los pesos correspondan al manifiesto.

Con los valores predeterminados basta el comando de Compose. Si quieres cambiar el puerto, las imágenes o la ruta de modelos, copia la plantilla a `apps/deploy/.env`, edita sus valores y vuelve a ejecutar el mismo comando. [Plantilla de configuración](apps/deploy/.env.example)

### Despliegue con Fly.io

Fly.io despliega la web y la API en una máquina en Virginia. Con `min_machines_running = 1`, Fly mantiene una máquina encendida en la región principal incluso cuando no hay tráfico.

El archivo [fly.toml](apps/deploy/fly/fly.toml) usa la etiqueta `latest` de cada imagen publicada por GitHub Actions. La API carga el modelo incluido en su imagen y utiliza un volumen de 5 GB para los EDF temporales. Cada archivo y sus metadatos se borran al terminar su análisis. Las cargas pendientes de iniciar caducan a los 10 minutos.

Para actualizar la aplicación desplegada, espera a que GitHub Actions publique las imágenes de los componentes que cambiaron. Con la sesión de Fly iniciada (`flyctl auth login`), ejecuta estos comandos desde la raíz del repositorio.

~~~bash
flyctl config validate --strict --config apps/deploy/fly/fly.toml
flyctl deploy --config apps/deploy/fly/fly.toml --ha=false
~~~

Tras un despliegue o reinicio, la API vuelve a cargar el modelo. El [estado de la API](https://sleepedfx.fly.dev/api/v1/health) indica `model_ready: true` cuando está listo.

### Configurar, comprobar y actualizar

| Parámetro | Dónde se cambia | Efecto |
|---|---|---|
| `LOCAL_WEB_PORT` | En la terminal al ejecutar el script Bash | Puerto de acceso en este equipo. Por defecto, `8081` en `127.0.0.1`. |
| `WEB_HOST_PORT` | `apps/deploy/.env` | Dirección y puerto publicados por Compose. El ejemplo local usa `127.0.0.1:8081` y la plantilla del servidor usa `80`. |
| `API_IMAGE`, `WEB_IMAGE` | `apps/deploy/.env` | Etiquetas de las imágenes que usa Compose. En local se usa `:local`. En el servidor se usan las imágenes de GHCR con `latest` o una etiqueta publicada `sha-…` de cada servicio. |
| `MODELOS_HOST_DIR` | `apps/deploy/.env` | Carpeta del anfitrión con los tres archivos. El valor inicial `../../modelos` es relativo a `apps/deploy/`. |
| `SLEEP_API_MAX_UPLOAD_BYTES` | `apps/deploy/.env` | Máximo por EDF en la API. Por defecto son `73400320` bytes (70 MiB). Puedes reducirlo. Para ampliarlo, ajusta también el formulario y el límite de Nginx. |

Comprueba el servicio con `docker compose -f apps/deploy/docker-compose.yml ps`. En local, la [salud de la API](http://127.0.0.1:8081/api/v1/health) debe indicar `model_ready: true`. Para detener ambos servicios, ejecuta `docker compose -f apps/deploy/docker-compose.yml stop`.

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

### Qué contiene la carpeta `datos/`

Git guarda un archivo `.dvc` por cada colección o archivo versionado. Por ejemplo, `datos/sleep-cassette.dvc` identifica la versión de las noches de Sleep Cassette que corresponde a este código. Al ejecutar `dvc pull`, DVC lee esos punteros, recupera los archivos de **Cloudflare R2** y reconstruye esta estructura en tu equipo.

~~~text
datos/
├── sleep-cassette/       Registros de sueño e hipnogramas de 153 noches de 78 personas.
├── sleep-telemetry/      Registros de sueño e hipnogramas de 44 noches de 22 personas.
├── sleep-anphy/          Registros y anotaciones para pruebas externas.
├── ST-subjects.xls       Metadatos de los participantes de Sleep Telemetry.
├── example.edf           Una noche de Sleep Telemetry para probar la aplicación.
├── processed/            Características por época, potencias espectrales y datos preprocesados.
├── experimentos/         Configuraciones, resultados y artefactos de los experimentos.
├── referencias/          Predicciones guardadas para comparar modelos sobre las mismas épocas.
└── evaluacion_80_20/     Pesos DART y CRNN y manifiesto del ajuste de evaluación por persona.
~~~

Los pesos que carga la API se encuentran en `modelos/`, en la raíz del repositorio. La carpeta `datos/evaluacion_80_20/` sirve para reproducir la evaluación. [Inventario de los datos](datos/README.md)

### Descargar los datos con DVC

**1. Solicita acceso a Cloudflare R2.** Pide a quien administra el bucket `proyecto-maestria-ia` que te comparta por privado un **Access Key ID** y una **Secret Access Key** con permiso de lectura. Los nueve punteros de esta revisión suman **28,25 GiB (unos 30,34 GB)** de datos. Para una descarga completa, prevé también espacio para la caché local de DVC.

**2. Instala DVC con soporte para S3**, el protocolo que usa R2. Desde la raíz del clon, crea un entorno virtual con `python -m venv .venv` (en Linux o macOS puedes usar `python3`). Si ya tienes el entorno, actívalo directamente.

| Terminal | Comando de activación |
|---|---|
| Linux o macOS (Bash o Zsh) | `source .venv/bin/activate` |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Git Bash en Windows | `source .venv/Scripts/activate` |

~~~text
python -m pip install "dvc[s3]==3.67.1"
dvc remote list
~~~

Deberías ver `r2` junto a `s3://proyecto-maestria-ia`. El repositorio ya define el remoto y el endpoint de Cloudflare. [Configuración de DVC](.dvc/config)

**3. Configura tus credenciales.** Sustituye ambos valores de ejemplo por las claves que recibiste. La opción `--local` las guarda en `.dvc/config.local`, un archivo excluido de Git.

~~~text
dvc remote modify --local r2 access_key_id TU_ACCESS_KEY_ID
dvc remote modify --local r2 secret_access_key TU_SECRET_ACCESS_KEY
~~~

**4. Descarga lo que necesites.** Para probar una noche real, descarga únicamente el EDF de ejemplo (unos 29 MB). Después podrás seleccionarlo en el formulario de la aplicación desde `datos/example.edf`.

~~~text
dvc pull datos/example.edf.dvc
~~~

Para recuperar **todo el contenido** de `datos/` y verificarlo, ejecuta estos comandos desde la raíz del repositorio.

~~~text
dvc pull
dvc status
~~~

`dvc status` permite comprobar que los datos locales coinciden con los punteros del clon. Si la descarga devuelve `AccessDenied`, comprueba con quien administra R2 que las claves correspondan a este bucket y tengan permiso de lectura.

### Reproducir los notebooks

Con los datos descargados y el entorno virtual activo, instala las dependencias con `python -m pip install -r requirements.txt` y abre `jupyter lab`. Si regeneras una colección como `datos/processed/`, revisa los cambios con `dvc status`. Quienes tengan acceso de escritura a R2 pueden registrar la colección con `dvc add datos/processed`, subir los datos con `dvc push` y guardar el puntero actualizado en Git. [EDA de Sleep Telemetry](Notebooks/EDA/EDA_Sleep_EEG_ST7242J0_datset/EDA_Sleep_EEG_dataset.ipynb)
