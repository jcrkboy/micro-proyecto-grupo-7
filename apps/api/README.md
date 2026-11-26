# Sleep-EDFx API

Backend FastAPI para cargar un PSG EDF y generar un hipnograma preliminar con
el bundle exportado por `Notebooks/dart_crnn_mixto_final_100.ipynb`.

## Preparación inicial

Todos los comandos deben ejecutarse desde la raíz de
`micro-proyecto-grupo-7`. La configuración del backend se encuentra en
`apps/api/.env`; puede crearse inicialmente copiando `apps/api/.env.example`.
El bundle configurado debe contener `manifest.json`, `dart.txt` y `crnn.keras`.

El servicio combina DART (59 %) y CRNN (41 %) en paralelo. Cada análisis requiere
al menos una derivación EEG a 100 Hz (`EEG Fpz-Cz` o `EEG Pz-Oz`). También admite
`EOG horizontal` a 100 Hz y `EMG submental` a 1 o 100 Hz. Los canales omitidos
aportan ceros en las entradas de ambos modelos. Con un solo EEG, las variables que
comparan ambas derivaciones también quedan a cero. Cuando se selecciona un EMG
de 1 Hz, la CRNN aprovecha la envolvente y DART conserva el valor ausente de su
configuración de entrenamiento para esos registros.

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
  -d '{"upload_id":"REEMPLAZAR_UUID","channels":["EEG Pz-Oz","EOG horizontal"]}'
```

Si se omite `channels`, la API utiliza todos los canales compatibles presentes.
Con una selección explícita, una combinación inválida devuelve HTTP 422.
El campo `channels` de la respuesta identifica las señales utilizadas.
También están disponibles `GET /health`, `GET /api/v1/health` y
`GET /api/v1/model`. La respuesta de inferencia incluye tiempos, estadio,
confianza y probabilidades por época, lista para graficar un hipnograma.

## Docker

El contexto de construcción es la raíz del repositorio:

```bash
docker build -f apps/api/Dockerfile -t sleep-edfx-api .
docker run --rm -p 8080:8080 \
  -v "sleep-uploads:/app/storage/uploads" \
  sleep-edfx-api
```

La imagen incluye el manifiesto y los pesos de `modelos/` en `/artifacts/model/`. El volumen `sleep-uploads` conserva los estudios cargados entre reinicios.

En los despliegues local y servidor con Compose, esa ruta se monta desde la carpeta de modelos del anfitrión. Los dos modos requieren los tres archivos en el equipo donde corre Docker. [Guía de despliegue](../deploy/README.md)
