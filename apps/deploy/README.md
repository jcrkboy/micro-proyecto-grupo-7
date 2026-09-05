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

2. Autenticacion contra GHCR: no hace falta. Los paquetes son publicos porque
   el repositorio lo es, asi que `docker compose pull` funciona sin login.

   Para comprobarlo desde una maquina sin sesion en GHCR, si el comando
   devuelve el manifiesto la imagen es publica:

   ```bash
   docker manifest inspect ghcr.io/jcrkboy/micro-proyecto-grupo-7-web:latest
   ```

   Si algun dia se vuelven privados, hace falta un Personal Access Token con
   alcance `read:packages`:

   ```bash
   echo "$GHCR_TOKEN" | docker login ghcr.io -u <usuario-github> --password-stdin
   ```

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
imagen nueva. El `pull` explicito no es opcional: `up` por si solo reutiliza la
capa `latest` que ya esta en el cache local y el despliegue quedaria en la
version anterior sin ningun error visible.

Verificacion:

```bash
docker compose ps
docker compose logs -f api
curl -f http://localhost/api/v1/model
```

## Prueba local antes de desplegar

El mismo archivo sirve para un smoke test en la maquina de desarrollo, sin pasar
por GHCR. Se construyen las imagenes con los nombres que declara el `.env` y
Compose las encuentra localmente:

```bash
# desde la raiz del repositorio
docker build -f apps/api/Dockerfile -t ghcr.io/jcrkboy/micro-proyecto-grupo-7-api:latest .
docker build -f apps/web/Dockerfile -t ghcr.io/jcrkboy/micro-proyecto-grupo-7-web:latest apps/web

cd apps/deploy
docker compose up -d
curl http://localhost:${WEB_HOST_PORT:-80}/api/v1/model
```

Para la prueba local conviene apuntar `HOST_MODEL_DIR` al directorio del modelo
del repositorio y usar un `WEB_HOST_PORT` libre, por ejemplo 8081.

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
