"""CRNN retrospectiva con contexto espectral nocturno y tres ventanas por segmento."""
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from scipy.ndimage import convolve1d
from scipy.special import softmax

from scripts.buscar_fusion_crnn import CLASES, CLAVES, SEMILLA, carpeta_redes, nombre_particion, particiones
from scripts.evaluar_v6_compacto import PASOS, bloques, posterior, preparar, transiciones

DESFASES = (0, 5, 10)


def contexto(x):
    """Todas las estadísticas se calculan sobre una sola noche, sin sus etiquetas."""
    q10, mediana, q90 = np.percentile(x.reshape(-1, x.shape[-1]), [10, 50, 90], axis=0)
    z = np.clip((x-mediana)/np.maximum(q90-q10, .05), -5, 5).astype("float32")
    media = z.mean(axis=1)
    triangular = np.r_[1:9, 7:0:-1].astype("float32")
    centro = convolve1d(media, triangular/triangular.sum(), axis=0, mode="nearest")
    extendida = np.pad(media, ((3, 0), (0, 0)), mode="edge")
    pasado = sum(extendida[i:i+len(media)] for i in range(4))/4
    return np.concatenate([x, z, np.broadcast_to(centro[:, None], x.shape),
                           np.broadcast_to(pasado[:, None], x.shape)], axis=2)


def desplazar(x, desfase, relleno=0):
    padding = [(desfase, -(len(x)+desfase) % PASOS)] + [(0, 0)]*(x.ndim-1)
    return np.pad(x, padding, constant_values=relleno).reshape(-1, PASOS, *x.shape[1:])


def cache_contexto(meta):
    firma = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    return carpeta_redes(meta)/"contexto-nocturno"/firma


def entrenar(meta, noches):
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "5")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
    import tensorflow as tf
    from tensorflow.keras import Model, layers
    tf.config.experimental.enable_op_determinism()
    cache = cache_contexto(meta)
    if all((cache/nombre_particion(r)/"prob.parquet").exists() for r in particiones()):
        return cache
    total = {rid: contexto(x) for rid, x in noches.items()}
    for reservas in particiones():
        destino = cache/nombre_particion(reservas)
        destino.mkdir(parents=True, exist_ok=True)
        archivo = destino/"prob.parquet"
        if archivo.exists():
            continue
        inicio = perf_counter()
        test = meta.ronda.isin(reservas)
        tr, te = meta[~test], meta[test]
        assert set(tr.subject_id).isdisjoint(te.subject_id)
        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(SEMILLA)
        rng = np.random.default_rng(SEMILLA)
        entrada = layers.Input((PASOS, 6, 96))
        z = layers.TimeDistributed(layers.Conv1D(48, 3, padding="same", activation="relu"))(entrada)
        z = layers.TimeDistributed(layers.Flatten())(z)
        z = layers.Dense(48, activation="relu")(z)
        z = layers.Dropout(.15)(z)
        z = layers.Bidirectional(layers.GRU(32, return_sequences=True))(z)
        pred = layers.Dense(len(CLASES), activation="softmax")(layers.Dropout(.20)(z))
        red = Model(entrada, pred)
        red.compile(optimizer=tf.keras.optimizers.Adam(.001), loss="sparse_categorical_crossentropy")
        counts = tr.real.value_counts().reindex(CLASES).to_numpy()
        weights = (counts.mean()/counts)**.35
        weights /= np.average(weights, weights=counts)
        targets = {}
        for rid, g in tr.groupby("record_id"):
            labels = np.full(len(total[rid]), -1, dtype="int32")
            labels[g.epoch_index] = pd.Categorical(g.real, categories=CLASES).codes
            targets[rid] = labels
        training = {}
        for offset in DESFASES:
            xs, ys = [], []
            for rid, labels in targets.items():
                y = desplazar(labels, offset, -1)
                keep = (y>=0).any(1)
                xs.append(desplazar(total[rid], offset)[keep])
                ys.append(y[keep])
            x, y = np.concatenate(xs), np.concatenate(ys)
            training[offset] = (x, y.clip(0), np.where(y>=0, weights[y.clip(0)], 0).astype("float32"))
        for epoch in range(15):
            x, y, w = training[DESFASES[epoch%3]]
            orden = rng.permutation(len(x))
            red.fit(x[orden], y[orden], sample_weight=w[orden], epochs=1, batch_size=64, shuffle=False, verbose=0)
        A, prior = transiciones(tr)
        ajuste = perf_counter()-inicio
        if len(reservas)==1:
            red.save(destino/"crnn.keras")
            np.savez(destino/"hmm.npz", A=A, prior=prior)
        inicio = perf_counter()
        filas = []
        for rid, g in te.groupby("record_id"):
            x_noche = total[rid]
            vistas = []
            for offset in DESFASES:
                v = red.predict(desplazar(x_noche, offset), batch_size=128, verbose=0)
                vistas.append(v.reshape(-1, len(CLASES))[offset:offset+len(x_noche)].astype("float64"))
            integral = softmax(np.log(np.maximum(vistas, 1e-10)).mean(axis=0), axis=1)
            probabilidades = {"una": posterior(vistas[0], A, prior), "red": integral, "hmm": posterior(integral, A, prior)}
            f = g[CLAVES].copy()
            for nombre, p in probabilidades.items():
                assert np.isfinite(p).all() and np.allclose(p.sum(1), 1)
                f[[nombre+"_"+c for c in CLASES]] = p[g.epoch_index]
            filas.append(f)
        info = dict(ajuste_s=ajuste, inferencia_s=perf_counter()-inicio, parametros=red.count_params(),
                    sujetos_train=sorted(tr.subject_id.unique()), sujetos_reservados=sorted(te.subject_id.unique()))
        (destino/"tiempo.json").write_text(json.dumps(info), encoding="utf8")
        temporal = archivo.with_suffix(".tmp")
        pd.concat(filas).to_parquet(temporal, index=False)
        temporal.replace(archivo)
        print(destino.name, round(ajuste, 1), "s", flush=True)
    return cache


if __name__ == "__main__":
    meta, _, noches, _, _ = preparar()
    entrenar(meta, noches)
