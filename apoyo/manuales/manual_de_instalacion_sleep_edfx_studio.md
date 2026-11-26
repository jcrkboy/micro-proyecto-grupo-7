# 🛠️ Manual de Instalación - Sleep-EDFx Studio (Grupo 7)

Este documento describe cómo desplegar **Sleep-EDFx Studio** —formado por un frontend Angular y una API FastAPI con DART y CRNN— en una máquina virtual Linux, por ejemplo una instancia AWS EC2.

El despliegue utiliza Docker Compose para ejecutar las imágenes publicadas por GitHub Actions en GitHub Container Registry (GHCR). La máquina virtual no compila el código: descarga y ejecuta las imágenes ya construidas.

## 1. Componentes del despliegue

La solución se ejecuta mediante dos servicios Docker:

| Servicio | Función |
| --- | --- |
| `api` | Backend FastAPI y motor de clasificación DART + CRNN. |
| `web` | Frontend Angular compilado y servido mediante nginx. También funciona como proxy hacia la API. |

Las imágenes publicadas son:

- `ghcr.io/jcrkboy/micro-proyecto-grupo-7-api`
- `ghcr.io/jcrkboy/micro-proyecto-grupo-7-web`

Cada compilación publica dos etiquetas:

- `latest`: versión más reciente, recomendada para pruebas.
- `sha-<commit>`: versión asociada a un commit concreto, recomendada para producción por facilitar la reproducibilidad.

Los archivos principales del despliegue se encuentran en `apps/deploy`:

| Archivo | Función |
| --- | --- |
| `docker-compose.yml` | Define los servicios `api` y `web`, sus volúmenes, puertos y dependencia. |
| `.env.example` | Plantilla de variables de entorno; debe copiarse como `.env`. |
| `README.md` | Documentación del procedimiento de despliegue y mantenimiento. |

## 2. Prerrequisitos del sistema

La máquina anfitriona debe contar con:

- Git.
- Docker Engine.
- Plugin Docker Compose.
- Acceso a Internet para descargar las imágenes desde GHCR.

Se recomienda utilizar Linux, por ejemplo Ubuntu 22.04 LTS. También es posible realizar una prueba local en macOS o Windows mediante WSL2.

Las imágenes del repositorio son públicas, por lo que normalmente no es necesario autenticarse en GHCR. Puede comprobarse con:

```bash
docker manifest inspect ghcr.io/jcrkboy/micro-proyecto-grupo-7-web:latest
```

Si las imágenes se hacen privadas, será necesario autenticarse con un token de GitHub que tenga el permiso `read:packages`:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <usuario-github> --password-stdin
```

## 3. Preparación de la máquina virtual

Estos pasos se realizan una sola vez.

### 3.1. Clonar el repositorio

Descargue el proyecto y acceda a su directorio:

```bash
git clone https://github.com/jcrkboy/micro-proyecto-grupo-7.git
cd micro-proyecto-grupo-7
```

### 3.2. Modelo predictivo

La imagen de la API incluye `manifest.json`, `dart.txt` y `crnn.keras` de `modelos/`. Durante el arranque, la API carga los archivos desde `/artifacts/model/`.

### 3.3. Configurar las variables de entorno

Acceda a la carpeta de despliegue y copie la plantilla:

```bash
cd apps/deploy
cp .env.example .env
```

Edite `.env` y revise los valores correspondientes al entorno:

```bash
${EDITOR:-vi} .env
```

La configuración de ejemplo incluye:

```dotenv
API_IMAGE=ghcr.io/jcrkboy/micro-proyecto-grupo-7-api:latest
WEB_IMAGE=ghcr.io/jcrkboy/micro-proyecto-grupo-7-web:latest
WEB_HOST_PORT=80
SLEEP_API_MODEL_DIR=/artifacts/model
SLEEP_API_UPLOAD_DIR=/app/storage/uploads
SLEEP_API_MAX_UPLOAD_BYTES=52428800
SLEEP_API_CORS_ORIGINS=["http://localhost"]
```

Aspectos importantes:

- `API_IMAGE` y `WEB_IMAGE` indican las imágenes que descargará Docker Compose.
- `WEB_HOST_PORT` es el puerto que se expondrá hacia el exterior. Su valor predeterminado es `80`.
- `SLEEP_API_MAX_UPLOAD_BYTES=52428800` limita los archivos cargados a 50 MB.
- Las rutas `SLEEP_API_MODEL_DIR` y `SLEEP_API_UPLOAD_DIR` son rutas internas de los contenedores y deben permanecer absolutas.

Para producción, se recomienda sustituir la etiqueta `latest` por una etiqueta `sha-<commit>` previamente publicada en GHCR.

## 4. Puesta en marcha

Desde `apps/deploy`, descargue las imágenes y levante los servicios:

```bash
cd apps/deploy
docker compose pull
docker compose up -d
```

El comando `docker compose pull` es necesario cuando se utiliza `latest`, ya que descarga la versión actualizada de GHCR. Si se omite, Docker Compose puede reutilizar una imagen antigua almacenada en la caché local sin mostrar un error.

Durante el arranque:

1. Se descarga la imagen del backend FastAPI con DART y CRNN.
2. Se descarga la imagen del frontend Angular servido por nginx.
3. Se inicia el servicio `api`.
4. Se inicia el servicio `web` cuando la API está saludable.
5. nginx sirve el frontend y redirige las peticiones `/api/` al backend.

El archivo `docker-compose.yml` no construye imágenes; únicamente las descarga y ejecuta.

## 5. Arquitectura de red

El contenedor `web` publica el puerto interno `4200` y lo asigna al puerto definido por `WEB_HOST_PORT` en la máquina anfitriona:

```text
WEB_HOST_PORT:4200
```

Por defecto, la aplicación queda disponible en el puerto `80`.

nginx cumple dos funciones:

- Sirve el bundle estático de Angular.
- Actúa como proxy inverso de las rutas `/api/`, enviándolas al servicio:

```text
http://api:8080
```

El servicio backend debe conservar exactamente el nombre `api`, porque nginx lo utiliza para localizarlo dentro de la red interna de Docker. El puerto `8080` no se publica directamente en el host.

Como el navegador accede al frontend y a la API mediante el mismo origen, no se requiere una configuración especial de CORS para el funcionamiento normal.

## 6. Persistencia de datos

El despliegue utiliza los siguientes almacenamientos:

### Archivos EDF cargados

Los estudios cargados se guardan en el volumen Docker `sleep-uploads`, montado en el contenedor como:

```text
/app/storage/uploads
```

### Modelo de IA

Cada imagen de la API contiene los pesos entrenados de su revisión. Para instalar un nuevo modelo, seleccione la etiqueta publicada en `API_IMAGE` y vuelva a crear el servicio con estos comandos.

```bash
docker compose pull api
docker compose up -d
```

## 7. Verificación del despliegue

Compruebe el estado de los contenedores:

```bash
docker compose ps
```

Los servicios `api` y `web` deben aparecer activos. Para revisar los registros en tiempo real:

```bash
docker compose logs -f api
```

También puede consultar los logs de todos los servicios:

```bash
docker compose logs -f
```

Verifique que la API puede cargar el modelo:

```bash
curl -f http://localhost/api/v1/model
```

Si se configuró otro puerto, utilícelo en la URL. Por ejemplo, con `WEB_HOST_PORT=8081`:

```bash
curl -f http://localhost:8081/api/v1/model
```

Para acceder al tablero desde un navegador:

- En una instalación local: `http://localhost` o `http://localhost:8081`.
- En una VM o instancia EC2: `http://<IP_PUBLICA>` o `http://<IP_PUBLICA>:<WEB_HOST_PORT>`.

## 8. Actualización de la aplicación

Cuando GitHub Actions publique una nueva imagen, actualice el despliegue con:

```bash
cd apps/deploy
docker compose pull
docker compose up -d
```

El mismo procedimiento sirve para actualizar el frontend, el backend o ambos, según las imágenes que hayan cambiado.

Los workflows de construcción se ejecutan sobre la rama `main` y están separados por ruta:

- `build-api.yml` se activa con cambios en `apps/api/**`, `packages/sleep-staging/**`, `modelos/**` o `.dockerignore`.
- `build-web.yml` se activa con cambios en `apps/web/**`.

Por ello, un cambio exclusivo en el frontend no reconstruye el backend, y viceversa. Ambos workflows también pueden ejecutarse manualmente mediante `workflow_dispatch`.

## 9. Prueba local antes de desplegar

Antes de utilizar GHCR, es posible realizar una prueba local construyendo las imágenes desde la raíz del repositorio:

```bash
docker build -f apps/api/Dockerfile \
  -t ghcr.io/jcrkboy/micro-proyecto-grupo-7-api:latest .

docker build -f apps/web/Dockerfile \
  -t ghcr.io/jcrkboy/micro-proyecto-grupo-7-web:latest apps/web
```

Configure un puerto libre para la prueba local.

```dotenv
WEB_HOST_PORT=8081
```

Después, inicie los servicios:

```bash
cd apps/deploy
docker compose up -d
curl http://localhost:8081/api/v1/model
```

## 10. Administración y mantenimiento

Detener temporalmente los servicios sin eliminar la configuración:

```bash
docker compose stop
```

Volver a iniciarlos:

```bash
docker compose start
```

Reiniciar un servicio concreto:

```bash
docker compose restart api
```

Eliminar los contenedores y la red creada por Compose:

```bash
docker compose down
```

El volumen `sleep-uploads` debe conservarse si se desea mantener los archivos EDF cargados. No utilice `docker compose down -v` salvo que también quiera eliminar los volúmenes y, con ellos, los datos persistidos.

## 11. Configuración del grupo de seguridad en AWS EC2

Abra hacia Internet únicamente el puerto configurado en `WEB_HOST_PORT`:

- Puerto `80` si se utiliza la configuración predeterminada.
- Puerto `8081`, por ejemplo, si se configuró `WEB_HOST_PORT=8081`.

No es necesario abrir el puerto `8080`, porque la API no se publica directamente en el host y solo es accesible internamente desde el contenedor `web`.

> 📌 **Nota para los evaluadores:**
> El proyecto puede ejecutarse en la instancia AWS EC2 asignada, siempre que estén disponibles Docker, Docker Compose, el archivo `.env`, las imágenes de la versión y las reglas de red indicadas en este manual.
