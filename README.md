# Sleep-EDFx Studio · Grupo 7

La aplicación genera un hipnograma a partir de un registro polisomnográfico EDF. La API usa el modelo DART + CRNN incluido en Git. [Despliegue con Docker Compose](apps/deploy/README.md) · [Manual de usuario](apoyo/manuales/manual_de_usuario_sleep_edfx_studio.md) · [EDF sintético de prueba](apps/api/tests/fixtures/sample_eeg_60s.edf)

**Integrantes** · Juan Carlos Gamboa Peñaranda, Jhoan Sebastián Saavedra Romero, Juan David Rozo Verástegui y Juan Javier Valera Mejías.

EEG polisomnografico del subset **Sleep Telemetry** de
[Sleep-EDFx](https://physionet.org/content/sleep-edfx/): 22 sujetos, 2 noches
cada uno (44 pares PSG + hipnograma, ~8 h a 100 Hz, epocas de 30 s).

**Sleep Cassette** aporta 153 noches de 78 personas, cada una con su PSG e
hipnograma. Junto con Telemetry hay 197 noches de 100 personas. El
[notebook mixto](Notebooks/dart_crnn_mixto.ipynb) entrena con 80 personas
(158 noches) y evalúa con 20 (39 noches). El
[ajuste final con las 100 personas](Notebooks/dart_crnn_mixto_final_100.ipynb)
se ejecuta aparte. Las características preprocesadas se conservan en
`datos/processed/`. Los punteros de [datos/](datos/) identifican la versión del dataset y del ajuste de evaluación. El [modelo final](modelos/) se obtiene al clonar el repositorio.

El experimento anterior comparó los dos modelos en las mismas épocas de la
entrega parcial, que incluía 12 noches completas de Cassette.
[Resultados y protocolo de evaluación](agent.md#comparación-directa-con-el-híbrido-v6).

---

## Setup

**1.** Crea el entorno virtual

```bash
python -m venv .venv
```

**2.** Activalo segun tu terminal

```bash
.venv\Scripts\activate           # PowerShell / cmd
source .venv/Scripts/activate    # Git Bash
source .venv/bin/activate        # Linux / macOS
```

**3.** Instala las dependencias

```bash
pip install -r requirements.txt
```

**4.** Configura las credenciales de R2 (pedirselas a quien administra el bucket)

```bash
dvc remote modify --local r2 access_key_id 'TU_ACCESS_KEY_ID'
dvc remote modify --local r2 secret_access_key 'TU_SECRET_ACCESS_KEY'
```

> **`--local` es obligatorio.** Escribe en `.dvc/config.local`, que esta
> ignorado. Sin esa bandera las credenciales se commitean al repositorio.

**5.** Descarga los datos y el ajuste de evaluación desde R2

```bash
dvc pull
```

**6.** Abre los notebooks de EDA, este paso ya opcional

```bash
jupyter lab
```

| Notebook | Alcance |
|---|---|
| `Notebooks/EDA/EDA_Sleep_EEG_ST7242J0_datset/EDA_Sleep_EEG_dataset.ipynb` | **Los 44 registros** (22 sujetos x 2 noches) |
| `Notebooks/EDA/EDA_Sleep_EEG_ST7242J0_individual/EDA_Sleep_EEG_ST7242J0.ipynb` | Un unico registro (`ST7242J0`), analisis de referencia |

El notebook de dataset completo recorre los 44 EDF (~75 s) y cachea las features en
`datos/processed/`; las ejecuciones siguientes cargan de ahi (~18 s).

---

## Estructura

```
.
├── apps/                           # Aplicaciones (backend, frontend, despliegue)
│   ├── api/                        # Backend FastAPI + LightGBM
│   │   ├── Dockerfile             # Imagen para la API
│   │   ├── .env.example            # Plantilla de configuracion
│   │   ├── run.sh                  # Script para ejecutar la API
│   │   ├── README.md               # Documentacion del backend
│   │   └── tests/
│   ├── web/                        # Frontend Angular
│   │   ├── Dockerfile             # Imagen para el frontend
│   │   └── ...                     # Codigo Angular
│   └── deploy/                     # Stack Docker Compose para producion
│       ├── docker-compose.yml      # Orquestacion de servicios (api + web)
│       ├── .env.example            # Variables de entorno para despliegue
│       └── README.md               # Guia de despliegue en VM
├── packages/                       # Librerias reutilizables
│   └── sleep-staging/              # Libreria de preprocesamiento e inferencia de sueno
│       ├── setup.py                # Configuracion del paquete
│       └── src/                    # Codigo fuente del paquete
├── Notebooks/
│   ├── dart_crnn_mixto.ipynb       # Evaluación por persona y ajuste final de DART + CRNN
│   └── experiments/                # Comparaciones y búsquedas en Telemetry y Cassette
│       ├── model_jhoan_saavedra_all_channels.ipynb   # Control LightGBM multicanal
│       ├── model_v6.ipynb           # Experimento CRNN + LightGBM + HMM de Colab
│       └── historicos/              # Modelos y búsquedas iniciales
├── Notebooks/EDA/                  # Análisis exploratorio de datos
│   ├── EDA_Sleep_EEG_ST7242J0/             # Export Markdown del EDA individual
│   ├── EDA_Sleep_EEG_ST7242J0_datset/      # EDA de los 44 registros
│   │   ├── EDA_Sleep_EEG_dataset.ipynb
│   │   └── img/*.png                       # Figuras exportadas
│   └── EDA_Sleep_EEG_ST7242J0_individual/  # EDA de un solo registro
│       ├── EDA_Sleep_EEG_ST7242J0.ipynb
│       └── img/*.png
├── scripts/                        # Scripts utilitarios
│   ├── generate_sample_edf.py      # Genera EDF de ejemplo para testing
│   └── run_lgbm_v2_candidate.py    # Script para entrenar candidato LightGBM v2
├── apoyo/
│   ├── manuales/                   # Instalación, uso y presentación
│   ├── matlab/                     # Script y figura de referencia
│   └── mlruns/                     # Ejecuciones locales de MLflow (ignoradas por Git)
├── docs/                           # Documentacion (MLOps Stack Canvas, reportes)
├── modelos/                        # Ajuste final de 100 personas, versionado en Git
│   ├── crnn.keras
│   ├── dart.txt
│   └── manifest.json
├── datos/                          # Estructura y punteros .dvc de cada colección
│   ├── evaluacion_80_20/           # Ajuste de evaluación recuperado con DVC
│   ├── ST-subjects.xls             # Metadatos de los 22 sujetos
│   ├── sleep-telemetry/            # 88 archivos EDF
│   │   ├── ST70xxJ0-PSG.edf        #   44 registros polisomnograficos
│   │   └── ST70xxJx-Hypnogram.edf  #   44 hipnogramas
│   ├── sleep-cassette/             # 153 PSG y 153 hipnogramas
│   ├── referencias/                # Predicciones LOSO de Telemetry para comparar por época
│   ├── experimentos/lightgbm_st_sc/ # Modelo mixto, hiperparámetros y esquema de características
│   └── processed/                  # Cache generado por EDA
│       ├── epochs_features.parquet
│       └── psd_record_stage.parquet
├── .dvc/
│   ├── config                      # Bucket y endpoint de R2 (versionado)
│   └── config.local                # Credenciales (ignorado)
├── .github/workflows/              # GitHub Actions CI/CD
├── .gitignore
├── .dockerignore
├── requirements.txt
└── README.md
```

---

## Trabajar con los datos

### Agregar datos nuevos

```bash
cp <archivo-nuevo> datos/sleep-telemetry/
dvc add datos/sleep-telemetry       # actualiza el puntero de la colección
git add datos/sleep-telemetry.dvc
git commit -m "data: describir que se agrego"
dvc push
```

DVC es content-addressable: solo se suben los archivos nuevos, no el dataset
completo.

> El notebook de EDA de dataset completo escribe su cache en `datos/processed/`, que
> esta dentro del directorio que rastrea DVC. Tras ejecutarlo, `dvc status` aparecera
> sucio: hay que registrarlo con el mismo flujo de arriba (`dvc add datos/processed` y `dvc push`).

### Traer cambios de datos hechos por otro

```bash
git pull
dvc pull                           # sincroniza las colecciones según sus punteros
```

### Comandos utiles

| Comando | Que hace |
|---|---|
| `dvc status` | Cambios locales en `datos/` sin registrar |
| `dvc status -c` | Diferencias entre la cache local y R2 |
| `dvc remote list` | Remotes configurados |
| `dvc checkout` | Restaura `datos/` desde la caché local |

---

## Problemas frecuentes

| Sintoma | Causa |
|---|---|
| `AccessDenied` en `push` | Token de R2 sin permiso de escritura |
| `AccessDenied` en `pull` | Credenciales ausentes o en `.dvc/config` en vez de `.dvc/config.local` |
| El notebook no encuentra los `.edf` | Falta `dvc pull` |
| `dvc: command not found` | Entorno virtual sin activar |
