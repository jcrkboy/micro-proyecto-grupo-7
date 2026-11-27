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


# Sleep-EDFx Studio: manual funcional de usuario

> [!WARNING]
> **Uso de apoyo profesional.** Sleep-EDFx Studio genera un hipnograma **preliminar**. El resultado requiere revisión de un experto en sueño y no constituye un diagnóstico clínico.

## Contenido

1. [Propósito y alcance](#1-propósito-y-alcance)
2. [Requisitos previos](#2-requisitos-previos)
3. [Recorrido general](#3-recorrido-general)
4. [Guía paso a paso](#4-guía-paso-a-paso)
5. [Caso de prueba: Jhon Doe 3](#5-caso-de-prueba-jhon-doe-3)
6. [Anexo técnico](#6-anexo-técnico)
7. [Solución de problemas](#7-solución-de-problemas)
8. [Limitaciones y uso responsable](#8-limitaciones-y-uso-responsable)

---

## 1. Propósito y alcance

Sleep-EDFx Studio es una aplicación web que recibe un registro polisomnográfico (PSG) en formato EDF y estima, para cada época de 30 segundos, el estadio de sueño correspondiente: vigilia (W), N1, N2, N3 o REM. Con esas predicciones construye un **hipnograma** interactivo y calcula el tiempo y el porcentaje que el registro pasa en cada estadio.

Todas las capturas provienen de una ejecución real con un archivo de prueba (paciente ficticio **Jhon Doe 3**).

## 2. Requisitos previos

| Elemento | Requisito |
|---|---|
| Navegador | Chrome, Edge, Firefox o Safari con Internet. No requiere instalación ni inicio de sesión. |
| Formato | EDF, **máximo 70 MiB**. |
| Frecuencia | Las señales que usa el modelo deben estar a **100 Hz**. |
| Señales obligatorias | Al menos un EEG: **Fpz-Cz** o **Pz-Oz**. |
| Señales opcionales | **EOG horizontal** y **EMG submental**. |
| Identificador | Nombre o código del estudio. Se recomienda un seudónimo. |

> [!NOTE]
> **Archivo de prueba:** `paciente_prueba.edf` (28,1 MiB). Contiene EEG Fpz-Cz, EEG Pz-Oz, EOG horizontal y EMG submental a 100 Hz, y un canal *Marker* que el modelo no usa. Duración: 9 h 58 min.

## 3. Recorrido general

La aplicación tiene una sola página que cambia de estado según el avance:

**Carga** → **Análisis** → **Resultados** → **Exportación o nuevo análisis**

| Elemento | Función |
|---|---|
| **Acerca de** | Panel con la descripción de la herramienta, las señales admitidas y el método de clasificación. |
| **Modelo disponible** | El punto verde indica que el servicio de inferencia está activo. |
| Tarjetas 100 Hz · 30 s · 5 | Frecuencia de muestreo, duración de cada época y número de estadios. |
| Aviso “Uso de apoyo profesional” | Recuerda que el resultado es preliminar. |

![Pantalla inicial de Sleep-EDFx Studio]()
<img width="1308" height="805" alt="01-pantalla-inicial" src="https://github.com/user-attachments/assets/b29059a5-200b-4018-98f7-4239d36873cd" />
*Figura 1. Pantalla inicial: descripción y parámetros del modelo a la izquierda, formulario “Carga del registro” a la derecha.*

## 4. Guía paso a paso

### Paso 1. Abrir la aplicación y verificar el modelo

1. Ingrese a <https://sleepedfx.fly.dev>.
2. Confirme que en la esquina superior derecha aparece **“Modelo disponible”** con el punto verde.

> [!TIP]
> Si la aplicación estuvo inactiva, el primer acceso puede tardar unos segundos mientras el servidor se activa.

### Paso 2. Consultar “Acerca de” (opcional)

Haga clic en **Acerca de** para ver qué calcula la herramienta, qué señales admite y cómo se obtiene el hipnograma. Para salir, pulse **Cerrar** o la tecla *Esc*.

### Paso 3. Ingresar el identificador del paciente

En **Nombre o identificador del paciente**, escriba el nombre o código del estudio. Este texto aparece luego como título de los resultados (“Resumen de …”). Por privacidad, use un seudónimo.

### Paso 4. Seleccionar el archivo EDF

1. Haga clic en **Selecciona un archivo EDF**.
2. Elija el archivo `.edf` en la ventana del sistema operativo.
3. La tarjeta muestra el nombre y el tamaño del archivo. Para cambiarlo, pulse **Reemplazar**.

> [!NOTE]
> El archivo **no se sube** al seleccionarlo. La transferencia comienza solo al pulsar **Analizar registro**.

### Paso 5. Revisar los canales del registro

Después de elegir el archivo aparece **Canales del registro**, con cada señal del EDF y su frecuencia:

- Los canales compatibles (EEG Fpz-Cz, EEG Pz-Oz, EOG horizontal y EMG submental a 100 Hz) vienen **marcados** por defecto.
- Los canales que el modelo no usa aparecen deshabilitados con la etiqueta **“Fuera del modelo”** (en el ejemplo, *Marker* a 10 Hz).
- Puede desmarcar señales, pero debe quedar **al menos un EEG** seleccionado.

<img src="img/02-carga-y-canales.jpg" alt="Formulario con archivo cargado y canales seleccionados" width="420">
<img width="400" height="670" alt="02-carga-y-canales" alt="Formulario con archivo cargado y canales seleccionados" src="https://github.com/user-attachments/assets/ece497c0-35b4-4d56-bed3-80a10f1220e7" />
*Figura 2. Formulario con identificador, archivo cargado y los cuatro canales compatibles seleccionados.*

### Paso 6. Ejecutar el análisis

Pulse **Analizar registro**. El progreso avanza por tres etapas:

| Etapa | Qué ocurre | Tiempo observado* |
|---|---|---:|
| **Subiendo archivo** | Envío del EDF al servidor, con barra y porcentaje. | 4,9 s |
| **Procesando señales** | Filtrado de las señales y extracción de características. | 31,8 s |
| **Clasificando etapas del sueño** | Inferencia de los dos modelos. Uno puede terminar antes mientras el otro prepara sus señales. | 0,4 s |

\* Registro de 28,1 MiB y 9 h 58 min. Tiempo total: 37,3 s.

<img src="img/03-analisis-en-curso.jpg" alt="Análisis del registro en curso" width="520">
<img width="672" height="448" alt="03-analisis-en-curso" src="https://github.com/user-attachments/assets/9b64bee4-0412-4569-83cd-6acb9850d9b6" />
*Figura 3. Subida completa; procesamiento de señales en curso.*

> [!TIP]
> **Cancelar** detiene el proceso y regresa al formulario. No cierre ni recargue la pestaña durante el análisis.

### Paso 7. Interpretar el resumen

Al terminar aparece **Análisis completado** y el título **Resumen de [identificador]**, con tres bloques:

1. **Encabezado técnico**: tiempo total y su desglose (carga, procesamiento, inferencia), número de épocas, versión del modelo y señales usadas.
2. **Tiempo analizado**: duración total clasificada (hh:mm:ss) y número de épocas.
3. **Distribución por estadio**: porcentaje y minutos en W, REM, N1, N2 y N3.

![Resumen de resultados](img/04-resumen-resultados.jpg)
<img width="1308" height="805" alt="04-resumen-resultados" src="https://github.com/user-attachments/assets/ade6b7e0-7494-4aa6-95bd-8c87f9138c8d" />
*Figura 4. Pantalla de resultados.*

> [!NOTE]
> Comprobación: épocas × 30 s = tiempo analizado. En el ejemplo, 1196 × 30 s = 598 min = 09:58:00.

### Paso 8. Explorar el hipnograma

El hipnograma muestra el estadio estimado de cada época a lo largo del registro. El eje vertical ordena los estadios (W, REM, N1, N2, N3) y el horizontal muestra el tiempo desde el inicio.

- **Acercar o alejar:** rueda del ratón o gesto de pellizco sobre el gráfico.
- **Desplazarse:** arrastre el gráfico o la barra de rango inferior.
- **Consultar una época:** pase el cursor para ver la hora, el estadio, el número de época y la **confianza**, con la probabilidad de cada estadio.

![Hipnograma completo](img/05-hipnograma.jpg)
<img width="1308" height="805" alt="05-hipnograma" src="https://github.com/user-attachments/assets/f5c17da7-88c9-47d1-964c-49cf7cebdb37" />
*Figura 5. Hipnograma completo del registro de prueba.*

![Detalle de una época](img/06-detalle-epoca.jpg)
<img width="1308" height="805" alt="06-detalle-epoca" src="https://github.com/user-attachments/assets/a55d28a8-d3b8-4106-b5b4-0e0d59d0ddb6" />
*Figura 6. Vista ampliada: la época 386 (03:12:30) se clasificó como N3 con 98,4 % de confianza.*

> [!TIP]
> Las épocas con probabilidades repartidas entre dos estadios (por ejemplo, N1 frente a W o N2) son las que más conviene verificar manualmente.

### Paso 9. Exportar los resultados

- **Descargar CSV**: tabla para hojas de cálculo, Python (pandas) o R.
- **Descargar JSON**: formato estructurado para integración o reprocesamiento.

### Paso 10. Iniciar un nuevo análisis

Pulse **Nuevo análisis** para volver al formulario. Descargue antes los resultados que quiera conservar: la interfaz no guarda historial.

## 5. Caso de prueba: Jhon Doe 3

Señales: EEG Fpz-Cz + EEG Pz-Oz + EOG horizontal + EMG submental · **09:58:00** analizadas · **1196** épocas · **37,3 s** de análisis.

| Estadio | Minutos | Porcentaje | Épocas* |
|---|---:|---:|---:|
| W (vigilia) | 159,5 | 26,7 % | 319 |
| N1 | 92,0 | 15,4 % | 184 |
| N2 | 219,0 | 36,6 % | 438 |
| N3 | 64,0 | 10,7 % | 128 |
| REM | 63,5 | 10,6 % | 127 |
| **Total** | **598,0** | **100 %** | **1196** |

\* Minutos × 2 (cada época dura 30 s).

**Lectura del hipnograma:**

- Los episodios de **N3** se concentran cerca de 03:10–03:25 y reaparecen hacia el final (07:30–08:40).
- El bloque de **REM** más largo aparece en la segunda mitad (06:20–07:00).
- El registro termina con casi una hora continua de **W**, que cuenta dentro del 26,7 % de vigilia.

> [!NOTE]
> Para métricas como la eficiencia del sueño, conviene acotar el análisis al periodo entre “luces apagadas” y “luces encendidas”. Los porcentajes de la aplicación se calculan sobre todo el registro.

## 6. Anexo técnico

| Parámetro | Valor |
|---|---|
| Entrenamiento | Registros de **100 personas** de Sleep-EDF Expanded (PhysioNet). |
| Unidad de clasificación | Época de **30 s**. |
| Clases | W, N1, N2, N3, REM. |
| Frecuencia de entrada | 100 Hz. |
| Señales | EEG Fpz-Cz, EEG Pz-Oz (al menos uno), EOG horizontal y EMG submental (opcionales). |
| Arquitectura | Ensamble de **LightGBM DART** (sobre características extraídas) y una red **CRNN** (convolucional y recurrente). |
| Versión del modelo | `dart_666_crnn_27_20261119_191036` |
| Salida por época | Estadio y probabilidad de cada clase. |
| Exportación | CSV y JSON. |
| Límite de archivo | 70 MiB. |

**Flujo:** EDF → detección de canales → preprocesamiento (filtrado y épocas de 30 s) → LightGBM DART + CRNN en paralelo → ensamble de probabilidades → hipnograma.

En la prueba, “procesamiento e inferencia coincidieron durante 0,3 s”: un modelo empezó a predecir mientras el otro seguía preparando sus señales. Los detalles internos de cada rama no se ven en la aplicación y se documentan en el informe técnico del proyecto.

## 7. Solución de problemas

| Situación | Qué hacer |
|---|---|
| No aparece “Modelo disponible” | Espere unos segundos y recargue la página. |
| Archivo mayor de 70 MiB | Recorte el registro o elimine canales que no usa el modelo. |
| No hay EEG seleccionable | Verifique que el EDF tenga Fpz-Cz o Pz-Oz a 100 Hz. |
| Canal “Fuera del modelo” | Es normal en canales auxiliares; no afecta al análisis. |
| El análisis tarda demasiado | Use **Cancelar** y reintente. |
| Analizar otro registro | Descargue los resultados y pulse **Nuevo análisis**. |

## 8. Limitaciones y uso responsable

- **Resultado preliminar:** debe revisarlo un especialista según el manual de la AASM.
- **Generalización:** el modelo se entrenó con Sleep-EDFx (Fpz-Cz/Pz-Oz, 100 Hz). Otros equipos, montajes o poblaciones pueden rendir menos.
- **Estadio N1:** es el de menor acuerdo incluso entre expertos. Revise con cuidado las épocas de N1 y las de baja confianza.
- **Periodo analizado:** las métricas incluyen la vigilia antes y después del sueño.
- **Privacidad:** el EDF se envía a un servidor externo. Use identificadores seudonimizados y registros anonimizados.



