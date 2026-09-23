# Acesco - Documentación de Producto

## Manual de Usuario: Sleep-EDFx Studio
**Plataforma de Pre-diagnóstico Clínico de Polisomnografía (PSG)**  
*Versión 1.0 — Septiembre de 2026*

> **Documento de Referencia:** Este documento está basado en el archivo original `Manual_de_Usuario_Sleep-EDFx_Studio.docx`.

---

## Tabla de Contenido
1. [Introducción](#introducción)
2. [Acceso a la Plataforma](#1-acceso-a-la-plataforma)
3. [Flujo de Trabajo Clínico](#2-flujo-de-trabajo-clínico)
   - [Paso 1: Carga del Estudio](#paso-1-carga-del-estudio-módulo-de-ingesta)
   - [Paso 2: Análisis del Resumen Estadístico](#paso-2-análisis-del-resumen-estadístico)
   - [Paso 3: Auditoría Médica](#paso-3-auditoría-médica-el-hipnograma-interactivo)
   - [Paso 4: Exportación de Resultados](#paso-4-exportación-de-resultados)

---

## Introducción

🩺 **Manual de Usuario - Sleep-EDFx Studio**

**Sleep-EDFx Studio** es una plataforma asistida por Inteligencia Artificial diseñada para optimizar el pre-diagnóstico clínico de estudios de polisomnografía (PSG). Este sistema procesa señales de electroencefalografía (EEG) para generar un hipnograma preliminar, resaltando áreas de baja confianza algorítmica para facilitar la revisión y auditoría por parte del especialista médico (Human-in-the-Loop).

> ⚠️ **Aviso Médico Importante:** Los resultados emitidos por esta plataforma son de carácter preliminar y de apoyo profesional. No constituyen un diagnóstico médico definitivo y requieren la revisión y aprobación de un especialista certificado.

---

## 1. Acceso a la Plataforma

Abra su navegador web (se recomienda Google Chrome o Mozilla Firefox) e ingrese a la dirección web proporcionada por el administrador del sistema (Ejemplo: `http://98.89.35.132`).

---

## 2. Flujo de Trabajo Clínico

### Paso 1: Carga del Estudio (Módulo de Ingesta)

Al ingresar a la plataforma, se encontrará con la pantalla de "Nuevo Estudio".

*   **Identificación:** Ingrese manualmente el nombre o el Identificador (ID) del paciente en el campo correspondiente.
*   **Carga del Archivo:** Arrastre y suelte el archivo del estudio polisomnográfico en el recuadro punteado, o haga clic para buscarlo en su computadora.
*   **Requisitos del archivo:** 
    *   Debe estar en formato `.edf`.
    *   No superar los 50 MB de tamaño.
    *   Estar muestreado a 100 Hz.
    *   Contener obligatoriamente los canales EEG `Fpz-Cz` y `Pz-Oz`.
*   **Procesamiento:** Haga clic en **"Procesar señal"**. El sistema verificará los canales y ejecutará el motor de Inteligencia Artificial de forma automática.

### Paso 2: Análisis del Resumen Estadístico

Una vez finalizado el procesamiento, la interfaz desplegará el panel de resultados:

*   En la parte superior, observará el **Resumen del Paciente**, que indica el tiempo total analizado (en épocas de 30 segundos).
*   A la derecha, verá un desglose porcentual y en minutos de la **arquitectura del sueño**: W (Vigilia), N1, N2, N3 (Sueño Profundo) y REM. Este panel le brinda un panorama general rápido de la salud del sueño del paciente.

### Paso 3: Auditoría Médica (El Hipnograma Interactivo)

La sección central contiene la **Secuencia Temporal (Hipnograma)**, la cual gráfica los estadios del sueño a lo largo de toda la noche. Aquí es donde el especialista ejerce su criterio médico:

*   **Navegación:** Deslice la barra inferior o utilice la rueda del ratón para explorar las diferentes horas del estudio.
*   **Nivel de Confianza:** Al pasar el cursor sobre cualquier época (bloque de 30 segundos), un panel flotante le indicará el estadio predicho y el porcentaje de confianza de la IA para esa decisión.
*   **Revisión de Alertas (Zonas Amarillas/Naranjas):** Preste especial atención a las épocas marcadas con alertas visuales de baja confianza. El sistema le sugiere auditar manualmente estas áreas de transición complejas (generalmente estadios N1 o REM).
*   **Visor de Ondas:** *(Si está habilitado en su vista)*, al hacer clic sobre una época dudosa, podrá observar las trazas crudas de las señales de EEG para emitir su propio juicio clínico.

### Paso 4: Exportación de Resultados

Una vez que haya revisado el hipnograma y validado las alertas generadas por la IA:

1.  Diríjase a la esquina superior derecha del panel de resultados.
2.  Seleccione **"Descargar CSV"** o **"Descargar JSON"**.
3.  El sistema descargará un archivo estructurado con el dictamen época por época, el cual puede ser adjuntado a la historia clínica del paciente o utilizado para alimentar su software de reportes institucionales.

> 💡 **Nota:** Para analizar un nuevo paciente, simplemente haga clic en el botón oscuro **"Nuevo análisis"** y repita el proceso.