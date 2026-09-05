# Frontend Sleep-EDFx

Aplicación Angular standalone para cargar un PSG EDF, solicitar la inferencia al
backend y visualizar el hipnograma preliminar. Usa Tailwind CSS y Apache ECharts.

La portada muestra el formulario hasta completar el primer análisis. Después,
el resultado reemplaza esa sección y el botón `Nuevo análisis` reutiliza el mismo
formulario dentro de un diálogo modal, sin descartar el resultado anterior hasta
que la siguiente inferencia termina correctamente.

## Ejecución local

La API debe estar disponible en `http://127.0.0.1:8080`. El servidor de
desarrollo redirige automáticamente `/api/*` mediante `proxy.conf.json`.

```bash
npm install
npm start
```

La interfaz queda disponible en `http://localhost:4200`.

## Configuración de la API

La URL base está centralizada en:

- `src/environments/environment.ts` para desarrollo;
- `src/environments/environment.production.ts` para producción.

Los dos ambientes usan actualmente la ruta relativa `/api/v1`. En desarrollo,
`proxy.conf.json` la dirige a `http://127.0.0.1:8080`; en producción, Nginx la
dirige al servicio `api:8080`. Esto permite alojar frontend y API bajo el mismo
dominio sin incrustar una dirección particular en el bundle.

## Archivo de ejemplo

Desde la pantalla de carga puede seleccionarse `data/example.edf`. Es el PSG
nocturno real y anonimizado `ST7011J0-PSG.edf` de Sleep-EDF Expanded, publicado
por PhysioNet bajo Open Data Commons Attribution License v1.0. Contiene los
canales `EEG Fpz-Cz` y `EEG Pz-Oz` a 100 Hz, dura 35.900 segundos y produce
1.196 épocas completas de 30 segundos.

Fuente: <https://physionet.org/content/sleep-edfx/1.0.0/sleep-telemetry/>

## Verificación

```bash
npm run test:ci
npm run e2e
npm run build
```

Las pruebas cubren validación del formulario, contrato del cliente HTTP,
transformación de épocas al hipnograma y exportación CSV. La compilación de
producción se genera en `dist/sleep-edfx-web/browser`.

La primera vez que se ejecuten las pruebas visuales, instale Chromium para
Playwright con `npx playwright install chromium`. La prueba end-to-end controla
el orden `Cargando archivo…` → `Procesando señal…` y verifica directamente los
píxeles de los cinco colores dentro del canvas de ECharts. También comprueba que
las épocas vecinas iguales formen barras continuas, que un salto entre estadios
tenga segmentos verticales del color de cada fila atravesada y que no existan
errores de consola. Finalmente mueve el mouse sobre una fila vacía y verifica
que la guía vertical seleccione la época por su posición horizontal y muestre
confianza y probabilidades. También verifica el reemplazo de la portada, el
foco y cierre del modal, el bloqueo del cierre durante el procesamiento y la
conservación del resultado anterior mientras llega la nueva respuesta.

## Contenedor

```bash
docker build -t sleep-edfx-web apps/web
docker run --rm -p 4200:4200 sleep-edfx-web
```

El contenedor sirve la interfaz de forma independiente. Para analizar archivos,
Nginx espera resolver un servicio llamado `api` en el puerto 8080; el
`compose.yaml` de la siguiente fase establecerá esa red y dependencia.

## Alcance clínico

El resultado usa únicamente `EEG Fpz-Cz` y `EEG Pz-Oz` a 100 Hz. Es una ayuda
preliminar para revisión profesional y no constituye un diagnóstico.
