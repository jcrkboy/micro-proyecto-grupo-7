# Datos del proyecto

Git conserva aquí la estructura del dataset. Cada puntero `.dvc` identifica una colección o un archivo en el remoto R2. Desde la raíz del repositorio, `dvc pull` recupera el conjunto completo y `dvc pull datos/example.edf.dvc` descarga solo el registro de ejemplo.

| Ruta después de la descarga | Contenido |
| --- | --- |
| `sleep-telemetry/` | 44 noches de 22 personas, cada una con un PSG y un hipnograma EDF. |
| `sleep-cassette/` | 153 noches de 78 personas, con sus señales y anotaciones. |
| `sleep-anphy/` | Registros externos de prueba con sus anotaciones. |
| `ST-subjects.xls` | Metadatos de los participantes de Telemetry. |
| `example.edf` | PSG de la noche ST7011J0 para probar la aplicación. |
| `evaluacion_80_20/` | Pesos DART y CRNN, y manifiesto del ajuste de evaluación de 80 personas. |
| `processed/` | Características y cachés de preprocesamiento. |
| `experimentos/` y `referencias/` | Recetas de entrenamiento, resultados y artefactos de comparación. |

Las fichas de entrenamiento y las salidas históricas conservan las rutas de la corrida que las generó.

Para probar la API con un archivo pequeño, el clon de Git incluye un [EDF sintético de 60 segundos](../apps/api/tests/fixtures/sample_eeg_60s.edf). Los pesos que carga la aplicación están en [modelos](../modelos/).
