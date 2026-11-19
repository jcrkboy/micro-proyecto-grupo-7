"""Evalúa la rama compacta de V6 con las particiones y modelos DART de la comparación justa."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import gettempdir
from time import perf_counter

import numpy as np
import pandas as pd
from lightgbm import Booster, LGBMClassifier
from scipy.fft import rfft
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
JUSTA = ROOT / ".sleep-cv/8f83a22b1d3a65d3"
FUSION = ROOT / ".sleep-cv/fusion-crnn/663d52206f296fcc"
SPEC = json.loads((ROOT / "data/experimentos/lightgbm_st_sc/experimento.json").read_text("utf8"))
CLASES = np.array(SPEC["classes"])
PASOS = 15
PESO_DART = .75
BANDAS = [(0.3, 4), (4, 8), (8, 12), (12, 16), (16, 30), (30, 35)]


def preparar():
    """Cada fila del manifiesto se enlaza a su posición en el EDF original."""
    import sys
    sys.path.insert(0, str(ROOT / "packages/sleep-staging/src"))
    from sleep_staging import PreprocessingConfig, PreprocessingPipeline
    from sleep_staging.datasets import discover_sleep_cassette_records, discover_sleep_telemetry_records
    from sleep_staging.training import load_or_build_supervised_dataset

    start = perf_counter()
    controles = pd.concat([pd.read_parquet(FUSION / f"ronda-{i}.parquet").assign(ronda=i)
                           for i in range(1, 6)], ignore_index=True)
    keys = ["record_id", "epoch_index"]
    assert not controles.duplicated(keys).any() and controles.groupby("subject_id").ronda.nunique().eq(1).all()
    dsdir = ROOT / "data"
    st = discover_sleep_telemetry_records(dsdir / "sleep-telemetry")
    sc = discover_sleep_cassette_records(dsdir / "sleep-cassette")
    grupos = [(st, "telemetry", dsdir / "processed/supervised")]
    grupos.extend(([r], "cassette", Path(gettempdir()) / "sleep-edfx-sc-features-v1") for r in sc)
    pred = np.full((len(controles), len(CLASES)), np.nan)
    modelos = [Booster(model_file=str(JUSTA / "tiempos-ronda-1/dart.txt"))]
    modelos.extend(Booster(model_file=str(FUSION / f"dart-{i}.txt")) for i in range(2, 6))
    for records, kind, cache in grupos:
        ds = load_or_build_supervised_dataset(records, PreprocessingPipeline(
            PreprocessingConfig(**SPEC["preprocessing_" + kind])), cache, verbose=False)
        ids = controles.reset_index().merge(ds.metadata[keys].reset_index(drop=True).reset_index(names="fila"),
                                            on=keys, validate="one_to_one")
        for ronda, g in ids.groupby("ronda"):
            x = ds.features.iloc[g.fila].reindex(columns=SPEC["feature_columns"]).astype("float32")
            pred[g["index"]] = modelos[ronda-1].predict(x, num_threads=4)
    assert np.allclose(pred.sum(1), 1) and np.array_equal(CLASES[pred.argmax(1)], controles.DART)
    segundos_dart = perf_counter()-start
    start = perf_counter()
    noches = {}
    freqs = np.fft.rfftfreq(500, 1/100)
    ventana = np.hanning(500).astype("float32")[None, None, :, None]
    for rid, g in controles.groupby("record_id"):
        raw = np.load(JUSTA / f"{rid}-signal.npy", mmap_mode="r")
        assert raw.shape[1:] == (3000, 4)
        x = np.empty((len(raw), 6, 4*len(BANDAS)), dtype="float32")
        for offset in range(0, len(raw), 100):
            chunk = raw[offset:offset+100].reshape(-1, 6, 500, 4)
            power = np.abs(rfft(chunk*ventana, axis=2))**2 / 500
            x[offset:offset+len(chunk)] = np.concatenate([
                np.log1p(power[:, :, (freqs >= a) & (freqs < b)].mean(axis=2))
                for a, b in BANDAS], axis=-1)
        assert np.isfinite(x).all()
        noches[rid] = x
    return controles, pred, noches, segundos_dart, perf_counter()-start


def transiciones(train):
    counts = np.ones((len(CLASES), len(CLASES)))
    initial = np.ones(len(CLASES))
    for _, g in train.sort_values("epoch_index").groupby("record_id"):
        y = pd.Categorical(g.real, categories=CLASES).codes
        sigue = np.diff(g.epoch_index) == 1
        np.add.at(counts, (y[:-1][sigue], y[1:][sigue]), 1)
        np.add.at(initial, y[np.r_[True, ~sigue]], 1)
    return counts/counts.sum(1, keepdims=True), initial/initial.sum()


def posterior(prob, trans, inicio):
    alpha = np.empty_like(prob)
    alpha[0] = inicio*prob[0]
    alpha[0] /= alpha[0].sum()
    for t in range(1, len(prob)):
        alpha[t] = (alpha[t-1] @ trans)*prob[t]
        alpha[t] /= alpha[t].sum()
    beta = np.ones(len(CLASES))
    post = alpha.copy()
    for t in range(len(prob)-2, -1, -1):
        beta = trans @ (prob[t+1]*beta)
        beta /= beta.sum()
        post[t] *= beta
    return post/post.sum(1, keepdims=True)


def bloques(x):
    return np.pad(x, [(0, -len(x) % PASOS)] + [(0, 0)]*(x.ndim-1)).reshape(-1, PASOS, *x.shape[1:])


def evaluar(ronda, controles, p_dart, noches):
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf
    from tensorflow.keras import Model, layers
    from threadpoolctl import threadpool_limits

    train = controles.loc[controles.ronda.ne(ronda)]
    test = controles.loc[controles.ronda.eq(ronda)]
    assert set(train.subject_id).isdisjoint(test.subject_id)
    firma = hashlib.sha256(Path(__file__).read_bytes() + (ROOT / "data.dvc").read_bytes())
    firma.update(pd.util.hash_pandas_object(controles, index=True).values.tobytes())
    firma.update(np.ascontiguousarray(p_dart).tobytes())
    out = ROOT / ".sleep-cv/v6-compacto" / firma.hexdigest()[:16] / str(ronda)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = out / "tiempo.json"
    if checkpoint.exists():
        return pd.read_parquet(out / "predicciones.parquet"), json.loads(checkpoint.read_text())

    start = perf_counter()
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(42)
    entradas, etiquetas, pesos = [], [], []
    counts = train.real.value_counts().reindex(CLASES).to_numpy()
    weight = (counts.mean()/counts)**.35
    weight /= np.average(weight, weights=counts)
    for rid, g in train.groupby("record_id"):
        y = np.full(len(noches[rid]), -1, dtype="int32")
        y[g.epoch_index] = pd.Categorical(g.real, categories=CLASES).codes
        y = bloques(np.pad(y, (0, -len(y) % PASOS), constant_values=-1))
        sel = (y >= 0).any(1)
        y = y[sel]
        entradas.append(bloques(noches[rid])[sel])
        etiquetas.append(y.clip(0))
        pesos.append(np.where(y >= 0, weight[y.clip(0)], 0).astype("float32"))
    x_in = layers.Input((PASOS, 6, 24))
    x = layers.TimeDistributed(layers.Conv1D(32, 3, padding="same", activation="relu"))(x_in)
    x = layers.TimeDistributed(layers.Flatten())(x)
    x = layers.Dense(32, activation="relu")(x)
    x = layers.Dropout(.15)(x)
    z = layers.Bidirectional(layers.GRU(16, return_sequences=True), name="embedding")(x)
    probs = layers.Dense(len(CLASES), activation="softmax")(layers.Dropout(.2)(z))
    net = Model(x_in, probs)
    net.compile(optimizer=tf.keras.optimizers.Adam(.001), loss="sparse_categorical_crossentropy")
    net.fit(np.concatenate(entradas), np.concatenate(etiquetas), sample_weight=np.concatenate(pesos),
            epochs=12, batch_size=64, verbose=0)
    encoder = Model(x_in, z)
    fit_neural = perf_counter()-start

    def contexto(rid):
        entrada = bloques(noches[rid])
        emb = encoder.predict(entrada, batch_size=128, verbose=0).reshape(-1, 32)[:len(noches[rid])]
        return np.column_stack([np.vstack([emb[:1], emb[:-1]]), emb, np.vstack([emb[1:], emb[-1:]])])

    start = perf_counter()
    gtrain = train.groupby("record_id", sort=True)
    x = np.concatenate([contexto(rid)[g.epoch_index] for rid, g in gtrain])
    y = np.concatenate([pd.Categorical(g.real, categories=CLASES).codes for _, g in gtrain])
    head = LGBMClassifier(n_estimators=180, learning_rate=.06, num_leaves=31, max_depth=7,
                          min_child_samples=80, colsample_bytree=.8, reg_lambda=1.5,
                          class_weight="balanced", random_state=42, n_jobs=5, verbosity=-1)
    head.fit(x, y)
    assert np.array_equal(head.classes_, np.arange(len(CLASES)))
    A, prior = transiciones(train)
    fit_head = perf_counter()-start
    net.save(out / "crnn.keras")
    head.booster_.save_model(str(out / "cabezal.txt"))
    np.savez(out / "hmm.npz", A=A, prior=prior)
    start = perf_counter()
    m = test.copy()
    for rid, g in m.groupby("record_id"):
        raw = head.predict_proba(contexto(rid), validate_features=False)
        with threadpool_limits(limits=1, user_api="blas"):
            hmm = posterior(raw, A, prior)
        probs = hmm[g.epoch_index]
        assert np.allclose(probs.sum(1), 1)
        for col, p in [("V6 compacto", probs), ("DART + compacto sin HMM",
                       PESO_DART*p_dart[g.index]+(1-PESO_DART)*raw[g.epoch_index]),
                       ("DART + compacto con HMM", PESO_DART*p_dart[g.index]+(1-PESO_DART)*probs)]:
            m.loc[g.index, col] = CLASES[p.argmax(1)]
    tiempo = dict(ronda=ronda, crnn_s=fit_neural, embeddings_cabezal_hmm_s=fit_head,
                  ajuste_rama_s=fit_neural+fit_head, inferencia_rama_s=perf_counter()-start,
                  noches_prueba=test.record_id.nunique(), parametros=net.count_params())
    m.to_parquet(out / "predicciones.parquet")
    tmp = checkpoint.with_suffix(".tmp")
    tmp.write_text(json.dumps(tiempo))
    tmp.replace(checkpoint)
    return m, tiempo


def estadisticas(m):
    filas = []
    for col in ["DART", "DART + CRNN", "V6 compacto", "DART + compacto sin HMM", "DART + compacto con HMM"]:
        filas.append([col, f1_score(m.real, m[col], labels=CLASES, average="macro", zero_division=0),
                      accuracy_score(m.real, m[col]), cohen_kappa_score(m.real, m[col])])
    return pd.DataFrame(filas, columns=["Modelo", "F1 macro", "Exactitud", "Kappa"]).set_index("Modelo")
