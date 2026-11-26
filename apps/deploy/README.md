# Operación de Sleep-EDFx Studio

Desde la raíz del repositorio, elige el comando correspondiente. El servidor arranca directamente con Docker Compose 2.24 o posterior. Con los valores predeterminados basta un clon con `modelos/`. El archivo `.env` es opcional y permite personalizar la instalación. [Archivos de entorno opcionales en Docker Compose](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/#use-the-env_file-attribute)

| Entorno | Comando | Imágenes y acceso |
|---|---|---|
| Desarrollo local | `bash apps/deploy/desplegar-local.sh` | Construye las imágenes `sleep-edfx-api:local` y `sleep-edfx-web:local`. La web escucha en `127.0.0.1:8081`. |
| Servidor | `docker compose -f apps/deploy/docker-compose.yml up -d --pull always --wait` | Descarga `API_IMAGE` y `WEB_IMAGE` de GHCR. La plantilla expone la web en el puerto 80. |

La guía principal incluye la instalación desde un clon nuevo, los parámetros de puerto e imágenes y el primer análisis con un EDF de ejemplo. [Despliegue paso a paso](../../README.md#despliegue)

## Modelos y archivos persistentes

La API necesita `manifest.json`, `dart.txt` y `crnn.keras` en la carpeta del anfitrión indicada por `MODELOS_HOST_DIR`. La ruta predeterminada apunta a [modelos/](../../modelos/) en la raíz del clon. Para usar un directorio administrado por separado en la VM, coloca los tres archivos de la misma versión en `/modelos` y establece `MODELOS_HOST_DIR=/modelos` en `.env`. El usuario del contenedor necesita acceso de lectura a los archivos y acceso de paso al directorio.

| Recurso | Ubicación en la API | Configuración |
|---|---|---|
| Modelo activo | `/artifacts/model` | Carpeta del anfitrión montada en modo de solo lectura. `SLEEP_API_MODEL_DIR` define el destino dentro del contenedor. |
| Registros EDF cargados | `/app/storage/uploads` | Volumen Docker `sleep-uploads`. `SLEEP_API_UPLOAD_DIR` define el destino dentro del contenedor. |

La aplicación web y la API comparten origen a través de Nginx. Si se habilita otro cliente web de distinto origen para la API, `SLEEP_API_CORS_ORIGINS` acepta una lista JSON de orígenes. [Plantilla de configuración](.env.example)

## Publicación y actualización

Los workflows de GitHub Actions se ejecutan al subir a `main` cambios en cada componente. El de la API también observa los cambios en `modelos/` y en el paquete de inferencia. Las imágenes reciben `latest` y una etiqueta por commit. Cada servicio puede tener una etiqueta distinta. Para repetir un despliegue, guarda las dos etiquetas y la revisión de Git de los pesos. [Build de la API](../../.github/workflows/build-api.yml) · [Build de la web](../../.github/workflows/build-web.yml)

En la VM, actualiza el clon y las etiquetas que hayas fijado en `.env`, y ejecuta Compose. Los EDF se mantienen en el volumen. Si solo reemplazaste los pesos en disco y las imágenes siguen siendo las mismas, añade `--force-recreate` al comando `up` para que la API vuelva a leerlos.

~~~bash
git pull --ff-only
docker compose -f apps/deploy/docker-compose.yml up -d --pull always --wait
~~~

## Verificar y diagnosticar

Desde la raíz, consulta el estado de los servicios, las últimas líneas del registro y el puerto de acceso.

~~~bash
docker compose -f apps/deploy/docker-compose.yml ps
docker compose -f apps/deploy/docker-compose.yml logs --tail 80 api web
docker compose -f apps/deploy/docker-compose.yml port web 4200
~~~

En local se puede consultar `curl -fsS http://127.0.0.1:8081/api/v1/health`. La respuesta debe indicar `status: ok` y `model_ready: true`. En el servidor usa el mismo sufijo `/api/v1/health` con el host y puerto de la instalación.

| Síntoma | Qué revisar |
|---|---|
| Falta un archivo del modelo | Comprueba los tres nombres, su tamaño y la ruta `MODELOS_HOST_DIR`. Las rutas relativas parten de `apps/deploy/`. |
| La API queda como `unhealthy` | Consulta sus logs. Si falla la comprobación de integridad, restaura los tres archivos de una misma revisión. |
| El puerto está ocupado | Para local usa `LOCAL_WEB_PORT=8090 bash apps/deploy/desplegar-local.sh`. En el servidor cambia `WEB_HOST_PORT` en `.env`. |
| Funciona en la VM pero no desde el navegador remoto | Comprueba el puerto que publica Compose y la regla de entrada del firewall o del grupo de seguridad de la VM. |

Para detener los servicios conservando las cargas, usa `docker compose -f apps/deploy/docker-compose.yml stop`.

### Prueba con navegador

Con el modo local en ejecución, esta prueba usa Chromium para cargar un EDF, analizarlo, abrir el hipnograma y descargar el resultado. Para ejecutar las pruebas de desarrollo se necesita Node.js 24 y npm en el equipo.

~~~bash
cd apps/web
npm ci
npx playwright install chromium
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8081 npm run e2e
~~~

La suite incluye un EDF sintético versionado en Git de 60 segundos (2 épocas). También prueba una noche de 1.196 épocas cuando está presente `datos/example.edf`. Puedes recuperar ese segundo registro con `dvc pull datos/example.edf.dvc` desde la raíz.
