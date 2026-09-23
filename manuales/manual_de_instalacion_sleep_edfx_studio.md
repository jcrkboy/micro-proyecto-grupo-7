# 🛠️ Manual de Instalación - Sleep-EDFx Studio (Grupo 7)

Este documento detalla los pasos necesarios para desplegar la plataforma Sleep-EDFx Studio (Tablero Angular y API en FastAPI) en un entorno local o servidor en la nube (ej. AWS EC2). 

El stack de ejecución no compila código directamente en el servidor: descarga las imágenes precompiladas que el pipeline de CI/CD en GitHub Actions publica en GitHub Container Registry (GHCR) desde la rama `main`. Esto garantiza un despliegue limpio y ágil.

## 1. Prerrequisitos del Sistema

Para ejecutar la aplicación, el entorno anfitrión debe contar con:
* Git (Para clonar el repositorio).
* Docker (Engine v20.10.0 o superior).
* Docker Compose (Plugin v2.0.0 o superior).

*Nota: Se recomienda un entorno Linux (ej. Ubuntu 22.04 LTS), macOS, o Windows utilizando WSL2.* No hace falta autenticación contra GHCR ya que los paquetes y el repositorio son públicos, por lo que la descarga de imágenes funciona sin inicio de sesión.

## 2. Preparación de la Máquina Virtual (Una sola vez)

Antes de levantar los contenedores, es necesario preparar los artefactos y variables de entorno:

**A. Ubicar el modelo predictivo**
Los binarios del modelo no viajan dentro de la imagen de Docker, por lo que deben colocarse en el host. 
1. Cree el directorio: `sudo mkdir -p /opt/sleep-edfx/model`
2. Transfiera los archivos `manifest.json` y `model.txt` desde la máquina de desarrollo a `/opt/sleep-edfx/model/` en la VM mediante `scp` o `dvc pull`.

**B. Configurar Variables de Entorno**
1. Copie la plantilla de configuración ejecutando: `cp .env.example .env`
2. Edite el archivo `.env` según corresponda para su entorno.

## 3. Paso a Paso del Despliegue

**Paso 1: Clonar el repositorio**
Descargue el código fuente del proyecto desde el repositorio oficial:
```bash
git clone https://github.com/jcrkboy/micro-proyecto-grupo-7.git
cd micro-proyecto-grupo-7
```

**Paso 2: Puesta en marcha**
Navegue al directorio de despliegue y ejecute los comandos para descargar la última versión y levantar la infraestructura:
```bash
cd apps/deploy
docker compose pull
docker compose up -d
```
*Importante: El comando `pull` explícito no es opcional, ya que garantiza que no se reutilice la capa de una versión anterior almacenada en caché local.*

**¿Qué sucede internamente?**
* Se descargarán las imágenes `ghcr.io/jcrkboy/micro-proyecto-grupo-7-api` (FastAPI + LightGBM) y `ghcr.io/jcrkboy/micro-proyecto-grupo-7-web` (bundle Angular servido por nginx).
* Se instanciarán dos contenedores sincronizados (API y Web) en la misma red interna.

## 4. Arquitectura y Persistencia

* **Red Interna:** El contenedor `web` publica el puerto 4200 y el host lo mapea a `WEB_HOST_PORT` (80 por defecto). Nginx sirve el frontend estático y actúa como proxy inverso, redirigiendo las peticiones `/api/` hacia `http://api:8080` dentro de la red de Compose. El backend no expone puertos directamente al host.
* **Persistencia:** Se utiliza un volumen Docker (`sleep-uploads`) para almacenar los archivos EDF cargados, y el directorio del modelo (`${HOST_MODEL_DIR}`) se monta como solo lectura. Para actualizar el modelo, basta con reemplazar los archivos en el host y ejecutar `docker compose restart api`.

## 5. Verificación y Acceso a la Plataforma

Para confirmar que los contenedores están operando correctamente, ejecute:
```bash
docker compose ps
```
Ambos contenedores deben aparecer con el estado `Up`.

**Acceso al Tablero:**
Abra su navegador y diríjase a `http://localhost` (o a la IP pública del servidor si está en la nube).

**Grupo de seguridad en AWS EC2:**
Asegúrese de abrir únicamente el puerto configurado en `WEB_HOST_PORT` (puerto 80) hacia internet. Al no exponer el backend al host, no se requieren reglas de entrada adicionales para la API.

## 6. Comandos de Administración y Mantenimiento

* **Ver registros (logs) en tiempo real:** `docker compose logs -f` (puede añadir `api` o `web` para un servicio específico).
* **Prueba de salud de la API:** `curl -f http://localhost/api/v1/model`
* **Detener servicios sin perder configuración:** `docker compose stop`
* **Destruir los contenedores:** `docker compose down`

---
> 📌 **Nota para los Evaluadores:**
Como parte del alcance del proyecto, este ecosistema ya se encuentra desplegado y funcionando de manera ininterrumpida en nuestra instancia asignada de AWS EC2, por lo que puede ser probado directamente en la IP pública notificada en el reporte técnico sin necesidad de realizar esta instalación local.