# Despliegue en VM

Stack de ejecucion para una maquina virtual Linux (por ejemplo EC2). No compila
codigo: descarga las imagenes que GitHub Actions publica en GHCR desde `main`.

## Piezas

| Archivo | Rol |
| --- | --- |
| `docker-compose.yml` | Define los servicios `api` y `web` apuntando a las imagenes publicadas |
| `.env.example` | Plantilla de configuracion; copiar a `.env` en la VM |

Imagenes publicadas:

- `ghcr.io/jcrkboy/micro-proyecto-grupo-7-api` — FastAPI + LightGBM (`apps/api/Dockerfile`)
- `ghcr.io/jcrkboy/micro-proyecto-grupo-7-web` — bundle Angular servido por nginx (`apps/web/Dockerfile`)

Cada una recibe dos etiquetas por build: `latest` y `sha-<commit>`. Para
reproducibilidad se recomienda fijar `sha-<commit>` en produccion y dejar
`latest` solo para entornos de prueba.

## Flujo de construccion

Los workflows corren solo sobre `main` y estan separados por ruta:

- `.github/workflows/build-api.yml` se dispara con cambios en `apps/api/**` o `packages/sleep-staging/**`.
- `.github/workflows/build-web.yml` se dispara con cambios en `apps/web/**`.

Un cambio que solo toca el frontend no reconstruye el backend, y viceversa.
Ambos aceptan ejecucion manual con `workflow_dispatch`.

## Preparacion de la VM (una sola vez)

1. Instalar Docker Engine y el plugin Compose.

2. Autenticar contra GHCR. Si el paquete es privado hace falta un Personal
   Access Token con alcance `read:packages`:

   ```bash
   echo "$GHCR_TOKEN" | docker login ghcr.io -u <usuario-github> --password-stdin
   ```

   Alternativa: marcar los paquetes como publicos en GitHub y omitir el login.

3. Colocar el artefacto del modelo en el host. Los binarios no viajan dentro de
   la imagen porque `data/` esta excluido en `.dockerignore`:

   ```bash
   sudo mkdir -p /opt/sleep-edfx/model
   # desde la maquina de desarrollo:
   scp data/models/sleep_staging_lightgbm_eeg_v2/{manifest.json,model.txt} \
     usuario@vm:/opt/sleep-edfx/model/
   ```

   Si la VM tiene credenciales de DVC configuradas, `dvc pull` es equivalente.

4. Copiar `docker-compose.yml` y crear el `.env`:

   ```bash
   cp .env.example .env
   ${EDITOR:-vi} .env
   ```

## Puesta en marcha y actualizacion

```bash
cd apps/deploy
docker compose pull
docker compose up -d
```

El mismo par de comandos actualiza el despliegue cuando Actions publica una
imagen nueva. `pull_policy: always` garantiza que `up` no reutilice una capa
`latest` obsoleta del cache local.

Verificacion:

```bash
docker compose ps
docker compose logs -f api
curl -f http://localhost/api/v1/model
```

## Red interna

El contenedor `web` publica el puerto 4200 y el host lo mapea a `WEB_HOST_PORT`
(80 por defecto). nginx sirve el bundle estatico y hace proxy de `/api/` hacia
`http://api:8080` dentro de la red de Compose. Por eso el servicio de backend
debe llamarse exactamente `api` y no necesita puerto publicado en el host.

Como el navegador consulta la API por el mismo origen, no hay CORS en juego en
el camino normal.

## Persistencia

- `sleep-uploads`: volumen Docker con los EDF cargados (`/app/storage/uploads`).
- `${HOST_MODEL_DIR}`: montado como solo lectura en `/artifacts/model`.

Reemplazar el modelo consiste en actualizar los archivos del host y reiniciar:
`docker compose restart api`.

## Grupo de seguridad en AWS

Abrir unicamente el puerto de `WEB_HOST_PORT` (80) hacia internet. El backend no
expone puertos al host, asi que no requiere reglas de entrada.
