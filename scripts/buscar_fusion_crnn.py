"""Busca el tamaño de la CRNN y la mezcla con DART, con prueba externa por persona."""
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score

from scripts.dart_interno_fusion import CLAVES, SEMILLA, VALIDACION, directorio, preparar_dart_interno, ruta_interna
from scripts.evaluar_v6_compacto import CLASES, PASOS, ROOT, bloques, posterior, preparar, transiciones

TAMANOS = {"Mini": (16, 16, 8), "Compacta": (32, 32, 16),
           "Mediana": (48, 48, 32), "Amplia": (64, 64, 48)}
PORCENTAJES = (100, 90, 85, 80, 75, 70, 65, 60, 50, 40, 25, 0)
EPOCAS = 12
LOTE = 64


def carpeta_redes(meta):
    import tensorflow as tf
    h = hashlib.sha256(Path(__file__).read_bytes() + (ROOT/"scripts/evaluar_v6_compacto.py").read_bytes())
    h.update(tf.__version__.encode())
    return directorio(meta)/h.hexdigest()[:16]


def particiones():
    reservas = {tuple(sorted((i, j))) for i, j in VALIDACION.items()}
    return sorted(reservas) + [(i,) for i in VALIDACION]


def nombre_particion(reservas):
    return "reserva-" + "-".join(map(str, reservas))


def entrenar_redes(meta, noches):
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "3")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
    import tensorflow as tf
    from tensorflow.keras import Model, layers

    tf.config.experimental.enable_op_determinism()
    rng = np.random.default_rng(SEMILLA)
    cache = carpeta_redes(meta)
    for reservas in particiones():
        grupo = nombre_particion(reservas)
        validacion = meta.ronda.isin(reservas)
        tr, te = meta[~validacion], meta[validacion]
        assert set(tr.subject_id).isdisjoint(te.subject_id)
        conteos = tr.real.value_counts().reindex(CLASES).to_numpy()
        pesos_clase = (conteos.mean()/conteos)**.35
        pesos_clase /= np.average(pesos_clase, weights=conteos)
        entradas, etiquetas, pesos = [], [], []
        for rid, g in tr.groupby("record_id"):
            y = np.full(len(noches[rid]), -1, dtype="int32")
            y[g.epoch_index] = pd.Categorical(g.real, categories=CLASES).codes
            y = np.pad(y, (0, -len(y) % PASOS), constant_values=-1).reshape(-1, PASOS)
            con_etiqueta = (y >= 0).any(1)
            y = y[con_etiqueta]
            entradas.append(bloques(noches[rid])[con_etiqueta])
            etiquetas.append(y.clip(0))
            pesos.append(np.where(y >= 0, pesos_clase[y.clip(0)], 0).astype("float32"))
        x, y, w = map(np.concatenate, (entradas, etiquetas, pesos))
        # Un único generador de NumPy. Se consumen los mismos sorteos al reanudar.
        ordenes = [rng.permutation(len(x)) for _ in range(EPOCAS)]
        A, prior = transiciones(tr)
        for nombre, (filtros, densas, gru) in TAMANOS.items():
            destino = cache/grupo/nombre
            destino.mkdir(parents=True, exist_ok=True)
            archivo = destino/"probabilidades.parquet"
            if archivo.exists():
                continue
            tf.keras.backend.clear_session()
            tf.keras.utils.set_random_seed(SEMILLA)
            entrada = layers.Input((PASOS, 6, 24))
            z = layers.TimeDistributed(layers.Conv1D(filtros, 3, padding="same", activation="relu"))(entrada)
            z = layers.TimeDistributed(layers.Flatten())(z)
            z = layers.Dense(densas, activation="relu")(z)
            z = layers.Dropout(.15)(z)
            z = layers.Bidirectional(layers.GRU(gru, return_sequences=True))(z)
            salida = layers.Dense(len(CLASES), activation="softmax")(layers.Dropout(.20)(z))
            red = Model(entrada, salida)
            red.compile(optimizer=tf.keras.optimizers.Adam(.001), loss="sparse_categorical_crossentropy")
            inicio = perf_counter()
            for orden in ordenes:
                red.fit(x[orden], y[orden], sample_weight=w[orden], epochs=1, shuffle=False,
                        batch_size=LOTE, verbose=0)
            ajuste = perf_counter()-inicio
            if len(reservas) == 1:
                red.save(destino/"crnn.keras")
                np.savez(destino/"hmm.npz", A=A, prior=prior)
            grupos = []
            inicio = perf_counter()
            for rid, g in te.groupby("record_id"):
                x_eval = noches[rid]
                prob = red.predict(bloques(x_eval), batch_size=128, verbose=0).reshape(-1, len(CLASES))[:len(x_eval)]
                p = posterior(prob.astype("float64"), A, prior)[g.epoch_index]
                assert np.isfinite(p).all() and np.allclose(p.sum(1), 1)
                tabla = g[CLAVES].copy()
                tabla[CLASES] = p
                grupos.append(tabla)
            datos = pd.concat(grupos)
            tiempos = dict(ajuste_crnn_s=ajuste, inferencia_crnn_hmm_s=perf_counter()-inicio,
                           parametros=red.count_params(), sujetos_train=sorted(tr.subject_id.unique()),
                           sujetos_reservados=sorted(te.subject_id.unique()))
            (destino/"medicion.json").write_text(json.dumps(tiempos), encoding="utf-8")
            temp = archivo.with_suffix(".tmp")
            datos.to_parquet(temp, index=False)
            temp.replace(archivo)
            print(grupo, nombre, f"{ajuste:.1f} s", flush=True)
    return cache


def probabilidades(ruta, meta):
    tabla = pd.read_parquet(ruta).set_index(CLAVES, verify_integrity=True)
    p = tabla.loc[pd.MultiIndex.from_frame(meta[CLAVES]), CLASES].to_numpy()
    assert np.isfinite(p).all() and np.allclose(p.sum(1), 1)
    return p


def f1_rapido(y, p):
    n = len(CLASES)
    cm = np.bincount(n*y+p, minlength=n*n).reshape(n, n)
    den = cm.sum(0)+cm.sum(1)
    return np.divide(2*cm.diagonal(), den, out=np.zeros(n), where=den!=0).mean()


def comparar(meta, dart, cache):
    internos = preparar_dart_interno(meta)
    elegidos, oof, reportes, parciales = [], [], [], []
    for i, j in VALIDACION.items():
        val, test = meta[meta.ronda.eq(j)], meta[meta.ronda.eq(i)]
        interno = cache/nombre_particion(tuple(sorted((i, j))))
        p_dart_val = probabilidades(ruta_interna(internos, i), val)
        y_val = pd.Categorical(val.real, categories=CLASES).codes.astype(int)
        mejor = -1
        for nombre in TAMANOS:
            p_red = probabilidades(interno/nombre/"probabilidades.parquet", val)
            for porcentaje in PORCENTAJES:
                mezcla = porcentaje*p_dart_val+(100-porcentaje)*p_red
                f1 = f1_rapido(y_val, mezcla.argmax(1))
                if f1 > mejor:
                    mejor, ganador, peso = f1, nombre, porcentaje
        elegidos.append([i, j, ganador, peso, mejor])
        # La selección está cerrada antes de puntuar la prueba de esta ronda.
        resultados = test[CLAVES+["subject_id", "cohorte", "real", "ronda", "DART"]].copy()
        y_test = pd.Categorical(test.real, categories=CLASES).codes.astype(int)
        for nombre in TAMANOS:
            carpeta = cache/nombre_particion((i,))/nombre
            p_red = probabilidades(carpeta/"probabilidades.parquet", test)
            medicion = json.loads((carpeta/"medicion.json").read_text())
            reportes.append([i, nombre, medicion["parametros"], medicion["ajuste_crnn_s"], medicion["inferencia_crnn_hmm_s"]])
            for porcentaje in PORCENTAJES:
                pred = (porcentaje*dart[test.index]+(100-porcentaje)*p_red).argmax(1)
                parciales.append((nombre, porcentaje, confusion_matrix(y_test, pred, labels=np.arange(len(CLASES)))))
                if nombre == ganador and porcentaje == peso:
                    resultados["Selección interna"] = CLASES[pred]
                if nombre == "Compacta" and porcentaje in (70, 75):
                    resultados[f"Compacta {porcentaje}/{100-porcentaje}"] = CLASES[pred]
        oof.append(resultados)
    oof = pd.concat(oof, ignore_index=True)
    assert len(oof)==len(meta) and not oof.duplicated(CLAVES).any() and not oof.isna().any().any()
    matrices = {}
    for nombre, porcentaje, cm in parciales:
        matrices[(nombre, porcentaje)] = matrices.get((nombre, porcentaje), 0)+cm
    tabla = []
    for (nombre, porcentaje), cm in matrices.items():
        assert cm.sum()==len(meta)
        f1 = 2*cm.diagonal()/(cm.sum(0)+cm.sum(1))
        acc = np.trace(cm)/cm.sum()
        azar = (cm.sum(0)/cm.sum()) @ (cm.sum(1)/cm.sum())
        tabla.append([nombre, porcentaje, f1.mean(), acc, (acc-azar)/(1-azar)])
    return (oof, pd.DataFrame(elegidos, columns=["Ronda","Validación interna","CRNN","% DART","F1 interno"]),
            pd.DataFrame(tabla, columns=["CRNN","% DART","F1 macro","Exactitud","Kappa"]),
            pd.DataFrame(reportes, columns=["Ronda","CRNN","Parámetros","Ajuste CRNN (s)","Inferencia CRNN + HMM (s)"]))


def metricas(tabla):
    filas = []
    for modelo in ["DART", "Compacta 75/25", "Compacta 70/30", "Selección interna"]:
        y, p = tabla.real, tabla[modelo]
        filas.append([modelo, len(y), f1_score(y, p, labels=CLASES, average="macro"),
                      accuracy_score(y, p), cohen_kappa_score(y, p)])
    return pd.DataFrame(filas, columns=["Modelo","Segmentos","F1 macro","Exactitud","Kappa"]).set_index("Modelo")


if __name__ == "__main__":
    meta, dart, noches, _, _ = preparar()
    entrenar_redes(meta, noches)
