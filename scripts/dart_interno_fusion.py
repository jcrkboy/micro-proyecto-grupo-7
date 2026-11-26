"""Ajustes internos de DART compartidos por los candidatos de la búsqueda de fusión."""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import gettempdir
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd

from scripts.evaluar_v6_compacto import CLASES, FUSION, ROOT, SPEC

SEMILLA = 42
# Ronda externa -> ronda interna de validación. La asignación es fija antes de puntuar.
VALIDACION = {1: 2, 2: 1, 3: 4, 4: 3, 5: 1}
CLAVES = ["record_id", "epoch_index"]


def directorio(meta):
    h = hashlib.sha256(Path(__file__).read_bytes())
    for puntero in sorted((ROOT / "datos").glob("*.dvc")):
        h.update(puntero.read_bytes())
    h.update(json.dumps(SPEC, sort_keys=True).encode())
    h.update(lgb.__version__.encode())
    h.update(pd.util.hash_pandas_object(meta[CLAVES+["subject_id", "real", "ronda"]], index=True).values.tobytes())
    return ROOT/".sleep-cv/busqueda-fusion-directa"/h.hexdigest()[:16]


def ruta_interna(cache, ronda):
    i, j = sorted((ronda, VALIDACION[ronda]))
    return cache/f"dart-reserva-{i}-{j}.parquet"


def preparar_dart_interno(meta):
    cache = directorio(meta)
    cache.mkdir(exist_ok=True, parents=True)
    pendientes = {ruta_interna(cache, r): (r, v) for r, v in VALIDACION.items()
                  if not ruta_interna(cache, r).exists()}
    if not pendientes:
        return cache
    sys.path.insert(0, str(ROOT/"packages/sleep-staging/src"))
    from sleep_staging import PreprocessingConfig, PreprocessingPipeline
    from sleep_staging.datasets import discover_sleep_cassette_records, discover_sleep_telemetry_records
    from sleep_staging.training import load_or_build_supervised_dataset

    data = ROOT/"datos"
    partes = [(discover_sleep_telemetry_records(data/"sleep-telemetry"), "telemetry", data/"processed/supervised")]
    partes.extend(([r], "cassette", Path(gettempdir())/"sleep-edfx-sc-features-v1")
                  for r in discover_sleep_cassette_records(data/"sleep-cassette"))
    X = np.empty((len(meta), len(SPEC["feature_columns"])), dtype="float32")
    indice = pd.MultiIndex.from_frame(meta[CLAVES])
    cargado = np.zeros(len(meta), dtype=bool)
    for registros, cohorte, carpeta in partes:
        ds = load_or_build_supervised_dataset(registros, PreprocessingPipeline(
            PreprocessingConfig(**SPEC["preprocessing_"+cohorte])), carpeta, verbose=False)
        filas = indice.get_indexer(pd.MultiIndex.from_frame(ds.metadata[CLAVES]))
        assert (filas >= 0).all() and not cargado[filas].any() and len(np.unique(filas)) == len(filas)
        np.testing.assert_array_equal(meta.real.iloc[filas], ds.labels)
        X[filas] = ds.features.reindex(columns=SPEC["feature_columns"]).to_numpy(dtype="float32")
        cargado[filas] = True
    assert cargado.all()

    def ajustar(item):
        destino, reservas = item
        retenidas = meta.ronda.isin(reservas).to_numpy()
        assert set(meta.subject_id[retenidas]).isdisjoint(meta.subject_id[~retenidas])
        print("Entrenando", destino.name, flush=True)
        inicio = perf_counter()
        modelo = lgb.LGBMClassifier(**dict(SPEC["parameters"], random_state=SEMILLA, n_jobs=3))
        modelo.fit(X[~retenidas], meta.real[~retenidas])
        np.testing.assert_array_equal(modelo.classes_, CLASES)
        datos = meta.loc[retenidas, CLAVES].copy()
        datos[CLASES] = modelo.booster_.predict(X[retenidas], num_threads=3)
        temporal = destino.with_suffix(".tmp")
        datos.to_parquet(temporal, index=False)
        temporal.replace(destino)
        print(destino.name, round(perf_counter()-inicio, 1), "s", flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(ajustar, pendientes.items()))
    return cache


if __name__ == "__main__":
    control = pd.concat([pd.read_parquet(FUSION/f"ronda-{i}.parquet").assign(ronda=i)
                         for i in VALIDACION], ignore_index=True)
    preparar_dart_interno(control)
