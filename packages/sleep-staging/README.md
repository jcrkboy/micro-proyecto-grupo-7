# sleep-staging

Paquete reutilizable de preprocesamiento EEG del proyecto Sleep-EDFx. Expone un
pipeline independiente de FastAPI, notebooks y etiquetas clínicas:

```python
from sleep_staging.preprocessing import PreprocessingPipeline

resultado = PreprocessingPipeline().transform_edf("registro-PSG.edf")
X = resultado.features
metadata = resultado.metadata
```

El pipeline exige los canales `EEG Fpz-Cz` y `EEG Pz-Oz`, valida la frecuencia
de 100 Hz, filtra la señal continua, crea épocas de 30 segundos, extrae las 81
features base del notebook de Juan Javier Valera, normaliza por registro y añade
contexto temporal hasta completar 486 columnas.

No usa el hipnograma ni recorta vigilia a partir de etiquetas. Esto permite que
la misma transformación se utilice tanto al entrenar como al servir el modelo.

## Utilidades de entrenamiento

Las dependencias de entrenamiento se instalan como un extra para no obligar al
backend a cargar MLflow, LightGBM o scikit-learn cuando no los necesite:

```bash
pip install -e ".[training]"
```

El notebook puede construir y dividir el dataset sin reimplementar funciones:

```python
from sleep_staging.training import build_supervised_dataset, split_by_subject

dataset = build_supervised_dataset(records, pipeline)
split = split_by_subject(dataset, validation_size=0.20, random_state=42)
```

La división se realiza por sujeto y mantiene sus dos noches en el mismo grupo.
Random Forest y LightGBM se crean mediante funciones diferentes; nunca se
sustituye silenciosamente un algoritmo por otro. MLflow se controla con
`MlflowConfig(enabled=False)` y permanece apagado por defecto.

Para optimizar hiperparámetros sin usar el holdout de validación:

```python
from sleep_staging.training import grouped_grid_search

result = grouped_grid_search(
    estimator=model,
    parameter_grid={"max_depth": [None, 20]},
    split=split,
    model_name="Random Forest",
    n_splits=3,
)
```

La búsqueda usa `GroupKFold` sobre los sujetos de training. El mejor estimador se
reentrena con todo training y se evalúa una sola vez sobre el conjunto de
validación reservado.
