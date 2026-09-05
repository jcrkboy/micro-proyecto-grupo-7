# Sleep-EDFx API

Backend FastAPI para cargar un PSG EDF y generar un hipnograma preliminar con
el bundle exportado por `Notebooks/model_jhoan_saavedra_preprocessing_v2.ipynb`.

## Preparación inicial

Todos los comandos deben ejecutarse desde la raíz de
`micro-proyecto-grupo-7`. La configuración del backend se encuentra en
`apps/api/.env`; puede crearse inicialmente copiando `apps/api/.env.example`.
El bundle configurado debe contener `manifest.json` y `model.txt`.

### Windows

En PowerShell, cree el entorno e instale las dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\packages\sleep-staging[inference,test]"
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
```

Desde Git Bash puede iniciar directamente el backend como ya fue probado:

```bash
apps/api/run.sh
```

Si se encuentra en PowerShell y tiene Git Bash disponible en el `PATH`, use:

```powershell
bash apps/api/run.sh
```

### Linux

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e "./packages/sleep-staging[inference,test]"
./.venv/bin/python -m pip install -e "./apps/api[dev]"
chmod +x apps/api/run.sh
./apps/api/run.sh
```

### macOS

Con Python 3 instalado —por ejemplo mediante Homebrew o el instalador oficial—:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e "./packages/sleep-staging[inference,test]"
./.venv/bin/python -m pip install -e "./apps/api[dev]"
chmod +x apps/api/run.sh
./apps/api/run.sh
```

En los tres sistemas la API queda disponible en `http://localhost:8080` y
Swagger en `http://localhost:8080/docs`. El script activa recarga automática de
forma predeterminada.

### Depuración

Después de instalar el extra `apps/api[dev]`, arranque `debugpy` desde Linux,
macOS o Git Bash:

```bash
DEBUG=true DEBUG_WAIT=true apps/api/run.sh
```

La API esperará un depurador en `127.0.0.1:5678`. En VS Code se puede usar una
configuración de tipo `debugpy`, solicitud `attach`, host `localhost` y puerto
`5678`. El depurador escucha localmente para no exponer un puerto sin
autenticación.

## Contrato MVP

1. Cargar un archivo y nombre:

```bash
curl -X POST http://localhost:8080/api/v1/uploads \
  -F "patient_name=Paciente de prueba" \
  -F "file=@apps/api/tests/fixtures/sample_eeg_60s.edf"
```

2. Copiar el `upload_id` de la respuesta y solicitar inferencia:

```bash
curl -X POST http://localhost:8080/api/v1/inferencia \
  -H "Content-Type: application/json" \
  -d '{"upload_id":"REEMPLAZAR_UUID"}'
```

También están disponibles `GET /health`, `GET /api/v1/health` y
`GET /api/v1/model`. La respuesta de inferencia incluye tiempos, estadio,
confianza y probabilidades por época, lista para graficar un hipnograma.

## Docker

El contexto de construcción es la raíz del repositorio:

```bash
docker build -f apps/api/Dockerfile -t sleep-edfx-api .
docker run --rm -p 8080:8080 \
  -v "$PWD/data/models/sleep_staging_lightgbm_eeg_v2:/artifacts/model:ro" \
  -v "sleep-uploads:/app/storage/uploads" \
  sleep-edfx-api
```

Los binarios del modelo no se incorporan en la imagen. En Linux deben montarse
en `/artifacts/model` o cambiar `SLEEP_API_MODEL_DIR` a una ruta persistente.
