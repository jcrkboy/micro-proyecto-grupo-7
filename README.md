# Micro-proyecto Grupo 7 — Estadios de sueno (Sleep-EDFx)

EEG polisomnografico del subset **Sleep Telemetry** de
[Sleep-EDFx](https://physionet.org/content/sleep-edfx/): 22 sujetos, 2 noches
cada uno (44 pares PSG + hipnograma, ~8 h a 100 Hz, epocas de 30 s).

El dataset (1.1 GB) se versiona con [DVC](https://dvc.org) sobre Cloudflare R2.
Git solo guarda el puntero `data.dvc`.

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

**5.** Descarga el dataset desde R2 (1.1 GB)

```bash
dvc pull
```

**6.** Abre los notebooks de EDA, este paso ya opcional

```bash
jupyter lab
```

| Notebook | Alcance |
|---|---|
| `EDA/EDA_Sleep_EEG_ST7242J0_datset/EDA_Sleep_EEG_dataset.ipynb` | **Los 44 registros** (22 sujetos x 2 noches) |
| `EDA/EDA_Sleep_EEG_ST7242J0_individual/EDA_Sleep_EEG_ST7242J0.ipynb` | Un unico registro (`ST7242J0`), analisis de referencia |

El notebook de dataset completo recorre los 44 EDF (~75 s) y cachea las features en
`data/processed/`; las ejecuciones siguientes cargan de ahi (~18 s).

---

## Estructura

```
.
├── data/                          # dataset (DVC, ignorado por Git)
│   ├── ST-subjects.xls            # metadatos de los 22 sujetos + noche placebo/temazepam
│   ├── sleep-telemetry/           # 88 archivos EDF
│   │   ├── ST70xxJ0-PSG.edf       #   44 registros polisomnograficos
│   │   └── ST70xxJx-Hypnogram.edf #   44 hipnogramas
│   └── processed/                 # cache generado por el EDA de dataset completo
│       ├── epochs_features.parquet    # una fila por epoca de 30 s (~42 700)
│       └── psd_record_stage.parquet   # PSD media por registro x estadio x canal
├── data.dvc                       # puntero al dataset (esto si va en Git)
├── EDA/
│   ├── EDA_Sleep_EEG_ST7242J0_datset/      # EDA de los 44 registros
│   │   ├── EDA_Sleep_EEG_dataset.ipynb
│   │   └── img/*.png                       # figuras exportadas
│   ├── EDA_Sleep_EEG_ST7242J0_individual/  # EDA de un solo registro
│   │   ├── EDA_Sleep_EEG_ST7242J0.ipynb
│   │   └── img/*.png
│   └── EDA_Sleep_EEG_ST7242J0/             # export en Markdown del EDA individual
├── docs/                          # MLOps Stack Canvas y reportes
├── requirements.txt
└── .dvc/
    ├── config                     # bucket y endpoint (versionado)
    └── config.local               # credenciales (ignorado)
```

---

## Trabajar con los datos

### Agregar datos nuevos

```bash
cp <archivos-nuevos> data/
dvc add data                       # recalcula el manifiesto
git add data.dvc
git commit -m "data: describir que se agrego"
dvc push
```

DVC es content-addressable: solo se suben los archivos nuevos, no el dataset
completo.

> El notebook de EDA de dataset completo escribe su cache en `data/processed/`, que
> esta dentro del directorio que rastrea DVC. Tras ejecutarlo, `dvc status` aparecera
> sucio: hay que registrarlo con el mismo flujo de arriba (`dvc add data` / `dvc push`).

### Traer cambios de datos hechos por otro

```bash
git pull
dvc pull                           # sincroniza data/ con lo que indica data.dvc
```

### Comandos utiles

| Comando | Que hace |
|---|---|
| `dvc status` | Cambios locales en `data/` sin registrar |
| `dvc status -c` | Diferencias entre la cache local y R2 |
| `dvc remote list` | Remotes configurados |
| `dvc checkout` | Restaura `data/` al estado que indica `data.dvc` |

---

## Problemas frecuentes

| Sintoma | Causa |
|---|---|
| `AccessDenied` en `push` | Token de R2 sin permiso de escritura |
| `AccessDenied` en `pull` | Credenciales ausentes o en `.dvc/config` en vez de `.dvc/config.local` |
| El notebook no encuentra los `.edf` | Falta `dvc pull` |
| `dvc: command not found` | Entorno virtual sin activar |
