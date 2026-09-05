# Sleep-EDFx API

Backend FastAPI para cargar un PSG EDF y generar un hipnograma preliminar con
el bundle exportado por `Notebooks/model_jhoan_saavedra_preprocessing_v2.ipynb`.

## Ejecución local

Desde la raíz de `micro-proyecto-grupo-7`:

```bash
python -m pip install -e "./packages/sleep-staging[inference,test]"
python -m pip install -e "./apps/api[test]"
uvicorn sleep_api.main:app --host 0.0.0.0 --port 8080
```

La configuración se toma de `apps/api/.env`. La plantilla versionada está en
`.env.example`. El bundle debe contener `manifest.json` y `model.txt`.

También puede iniciarse desde Linux, WSL o Git Bash mediante el script incluido:

```bash
bash apps/api/run.sh
```

El script activa recarga automática de forma predeterminada. Se puede cambiar la
dirección, el puerto o desactivar la recarga mediante variables:

```bash
HOST=127.0.0.1 PORT=8080 RELOAD=false bash apps/api/run.sh
```

### Depuración

Instale las dependencias de desarrollo y arranque `debugpy`:

```bash
python -m pip install -e "./packages/sleep-staging[inference]"
python -m pip install -e "./apps/api[dev]"
DEBUG=true DEBUG_WAIT=true bash apps/api/run.sh
```

La API esperará un depurador en `127.0.0.1:5678`. En VS Code se puede usar una
configuración de tipo `debugpy`, solicitud `attach`, host `localhost` y puerto
`5678`. Para aceptar conexiones desde otra máquina o contenedor se debe definir
conscientemente `DEBUG_HOST=0.0.0.0` y proteger el puerto; `debugpy` no aporta
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
