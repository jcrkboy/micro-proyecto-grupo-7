"""Compara los dos modelos guardados en noches de Cassette ajenas a ambos ajustes."""

import json
from pathlib import Path
from tempfile import gettempdir

import mne
import numpy as np
import pandas as pd
from lightgbm import Booster
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score
from tensorflow import keras

from sleep_staging import PreprocessingConfig, PreprocessingPipeline
from sleep_staging.datasets import discover_sleep_cassette_records, read_epoch_labels
from sleep_staging.training import load_or_build_supervised_dataset

ROOT = Path(__file__).resolve().parents[1]


def hybrid_inputs(record, channels, classes):
    """Reproduce el filtro, recorte de vigilia y z-score por época de V6."""
    raw = mne.io.read_raw_edf(record.psg_path, preload=True, verbose="ERROR")
    raw.pick(channels).reorder_channels(channels).filter(0.3, 35.0, verbose=False)
    if raw.info["sfreq"] != 100:
        raise ValueError(f"Frecuencia inesperada en {record.record_id}")
    n_epochs = raw.n_times // 3000
    labels = read_epoch_labels(record.hypnogram_path, n_epochs)
    asleep = np.flatnonzero(np.isin(labels, classes[1:]))
    keep = np.isin(labels, classes)
    if len(asleep):
        keep[:max(0, asleep[0] - 60)] = False
        keep[asleep[-1] + 61:] = False
    values = raw.get_data(stop=n_epochs * 3000) * 1e6
    epochs = values.reshape(len(channels), n_epochs, 3000).transpose(1, 2, 0)[keep]
    epochs = (epochs - epochs.mean(axis=1, keepdims=True)) / (epochs.std(axis=1, keepdims=True) + 1e-8)
    return np.flatnonzero(keep), labels[keep], epochs.astype("float32")


def contextual_embeddings(extractor, epochs, batch_size=16):
    """Usa la propia época de relleno en los extremos, como el generador V6."""
    blocks = []
    for start in range(0, len(epochs), batch_size):
        centers = np.arange(start, min(start + batch_size, len(epochs)))[:, None]
        indices = centers + np.arange(-7, 8)
        windows = epochs[np.where((indices >= 0) & (indices < len(epochs)), indices, centers)]
        inputs = {"seq_eeg": windows[..., :2], "seq_eog": windows[..., 2:3], "seq_emg": windows[..., 3:]}
        blocks.append(np.asarray(extractor(inputs, training=False), dtype=np.float32))
    current = np.concatenate(blocks)
    previous = np.vstack((current[:1], current[:-1]))
    following = np.vstack((current[1:], current[-1:]))
    return np.hstack((previous, current, following))


def decode_night(probabilities, transitions, prior):
    """Decodificación Viterbi independiente para cada registro."""
    emissions = np.log(probabilities + 1e-12)
    log_transitions = np.log(transitions + 1e-12)
    score = np.log(prior + 1e-12) + emissions[0]
    back = np.zeros_like(emissions, dtype=int)
    for t in range(1, len(emissions)):
        candidates = score[:, None] + log_transitions
        back[t] = candidates.argmax(axis=0)
        score = candidates.max(axis=0) + emissions[t]
    path = np.empty(len(emissions), dtype=int)
    path[-1] = score.argmax()
    for t in range(len(path) - 2, -1, -1):
        path[t] = back[t + 1, path[t + 1]]
    return path


def compare():
    model_dir = ROOT / "datos/experimentos/lightgbm_st_sc"
    ref = ROOT / "datos/referencias/hibrido_v6"
    spec = json.loads((model_dir / "experimento.json").read_text("utf-8"))
    hmm = json.loads((ref / "hmm.json").read_text("utf-8"))
    classes = np.array(hmm["classes"])
    trained = {r[:5] for r in hmm["training_records"] if r.startswith("SC")}
    reserved = set(spec["validation_subjects"]) - set(spec["train_subjects"]) - trained
    records = [r for r in discover_sleep_cassette_records(ROOT / "datos/sleep-cassette") if r.subject_id in reserved]
    if not records:
        raise ValueError("No hay noches de validación ajenas a ambos entrenamientos.")

    cnn = keras.models.load_model(ref / "modelo_crnn_maestro_optimo_v7.keras", compile=False)
    extractor = keras.Model(cnn.inputs, cnn.get_layer("embeddings_latentes_64d").output)
    hybrid = Booster(model_file=str(ref / "contextual_192d.txt"))
    tabular = Booster(model_file=str(model_dir / "model.txt"))
    pipeline = PreprocessingPipeline(PreprocessingConfig(**spec["preprocessing_cassette"]))
    frames = []
    for record in records:
        print(f"Evaluando {record.record_id}...", flush=True)
        idx, y, signals = hybrid_inputs(record, spec["preprocessing_telemetry"]["channels"], classes)
        probabilities = hybrid.predict(contextual_embeddings(extractor, signals))
        staged = load_or_build_supervised_dataset(
            [record], pipeline, Path(gettempdir()) / "sleep-edfx-sc-features-v1", verbose=False,
        )
        rows = pd.Index(staged.metadata.epoch_index).get_indexer(idx)
        if (rows < 0).any():
            raise ValueError("Faltan épocas emparejadas")
        np.testing.assert_array_equal(staged.labels.iloc[rows], y)
        features = staged.features.iloc[rows].reindex(columns=spec["feature_columns"])
        frames.append(pd.DataFrame({
            "registro": record.record_id, "época": idx, "real": y,
            "LightGBM mixto": np.array(spec["classes"])[tabular.predict(features).argmax(axis=1)],
            "V6 contextual": classes[probabilities.argmax(axis=1)],
            "V6 contextual + HMM": classes[decode_night(probabilities, np.array(hmm["A"]), np.array(hmm["pi"]))],
        }))
    return pd.concat(frames, ignore_index=True)


def summarize(results):
    rows = []
    groups = [*results.groupby("registro"), ("Conjunto", results)]
    for group, frame in groups:
        for column in ("LightGBM mixto", "V6 contextual", "V6 contextual + HMM"):
            y, pred = frame.real, frame[column]
            rows.append(dict(registro=group, modelo=column, épocas=len(frame),
                             accuracy=accuracy_score(y, pred), kappa=cohen_kappa_score(y, pred),
                             f1_macro=f1_score(y, pred, labels=["W", "N1", "N2", "N3", "REM"],
                                               average="macro", zero_division=0)))
    return pd.DataFrame(rows).set_index(["registro", "modelo"])


if __name__ == "__main__":
    print(summarize(compare()).round(4).to_string())
