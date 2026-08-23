# Micro-proyecto Grupo 7 — Estadios de sueno (Sleep-EDFx)

EEG polisomnografico del subset **Sleep Telemetry** de
[Sleep-EDFx](https://physionet.org/content/sleep-edfx/): 22 sujetos, 2 noches
cada uno (44 pares PSG + hipnograma, ~8 h a 100 Hz, epocas de 30 s).

El dataset (1.1 GB) se versiona con [DVC](https://dvc.org) sobre Cloudflare R2.
Git solo guarda el puntero `data.dvc`.

---

## Setup

```bash
python -m venv .venv
```

```bash
source .venv/Scripts/activate    # Git Bash (Windows)
# .venv\Scripts\activate         # PowerShell
# source .venv/bin/activate      # Linux / macOS
```

```bash
pip install -r requirements.txt
```

Credenciales de R2:

```bash
dvc remote modify --local r2 access_key_id 'TU_ACCESS_KEY_ID'
dvc remote modify --local r2 secret_access_key 'TU_SECRET_ACCESS_KEY'
```

> **`--local` es obligatorio.** Escribe en `.dvc/config.local`, que esta
> ignorado. Sin esa bandera las credenciales se commitean al repositorio.

```bash
dvc pull
```

```bash
jupyter lab
```

Abrir `EDA/EDA_Sleep_EEG_ST7242J0.ipynb`.

---

## Estructura

```
.
├── data/                          # dataset (DVC, ignorado por Git)
│   ├── ST-subjects.xls            # metadatos de los 22 sujetos
│   └── sleep-telemetry/           # 88 archivos EDF
│       ├── ST70xxJ0-PSG.edf       #   44 registros polisomnograficos
│       └── ST70xxJx-Hypnogram.edf #   44 hipnogramas
├── data.dvc                       # puntero al dataset (esto si va en Git)
├── EDA/
│   ├── EDA_Sleep_EEG_ST7242J0.ipynb
│   └── *.png                      # figuras exportadas
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
