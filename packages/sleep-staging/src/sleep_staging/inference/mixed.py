"""Inferencia DART y CRNN sobre una noche, sin etiquetas ni archivos del entrenamiento."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Lock

import mne
import numpy as np
from scipy.special import softmax

from sleep_staging.config import PreprocessingConfig
from sleep_staging.inference.artifacts import ModelManifest
from sleep_staging.inference.predictor import PredictionResult
from sleep_staging.inference.spectral import spectral_input, crnn_probabilities
from sleep_staging.preprocessing import PreprocessingPipeline
from sleep_staging.preprocessing.features import channel_prefix


class MixedSleepStagePredictor:
    def __init__(self, artifact_dir, *, require_final=False):
        from lightgbm import Booster
        from tensorflow import keras

        directory = Path(artifact_dir).resolve()
        spec = json.loads((directory / "manifest.json").read_bytes())
        if (
            spec["artifact_version"] != 2
            or spec["receta_crnn"] != "espectral-contextual-v1"
        ):
            raise ValueError("Formato de modelo mixto incompatible.")
        if require_final and spec["personas"] != 100:
            raise ValueError(
                "La API requiere el modelo final entrenado con 100 personas."
            )
        weights = {}
        for key in ("dart", "crnn"):
            entry = spec["archivos"][key]
            path = (directory / entry["nombre"]).resolve()
            if (
                path.parent != directory
                or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]
            ):
                raise ValueError(f"El archivo de {key} no corresponde al manifiesto.")
            weights[key] = path
        self.dart = Booster(model_file=str(weights["dart"]))
        self.crnn = keras.models.load_model(weights["crnn"], compile=False)
        self.channels = tuple(spec["canales"])
        self.bands = spec["bandas_hz"]
        self.offsets = spec["desfases"]
        mix = spec["fusion"]
        self.dart_weight, self.crnn_weight, self.floor = (
            mix["dart"],
            mix["crnn"],
            mix["piso"],
        )
        if (
            mix["tipo"] != "geometrica"
            or min(self.dart_weight, self.crnn_weight) < 0
            or not np.isclose(self.dart_weight + self.crnn_weight, 1)
            or not 0 < self.floor < 1
        ):
            raise ValueError("Configuración de fusión inválida.")
        classes = tuple(spec["clases"])
        if (
            len(set(classes)) != len(classes)
            or self.dart.num_model_per_iteration() != len(classes)
            or self.crnn.output_shape[-1] != len(classes)
        ):
            raise ValueError(
                "Las etapas de los modelos no coinciden con el manifiesto."
            )
        config = PreprocessingConfig(
            **spec["preprocesamiento_dart"], channels=self.channels
        )
        self.manifest = ModelManifest(
            spec["artifact_version"],
            spec["model_type"],
            weights["dart"].name,
            classes,
            tuple(self.dart.feature_name()),
            config,
            spec,
        )
        self.model_version = spec["version"]
        # Una noche en memoria por proceso; las dos ramas de esa noche sí avanzan en paralelo.
        self._lock = Lock()

    def _tabular(self, path, config, selected):
        result = PreprocessingPipeline(config).transform_edf(path)
        # LightGBM sustituye los espacios por guiones bajos al exportar los nombres.
        features = result.features.rename(columns=lambda name: name.replace(" ", "_"))
        missing = set(self.manifest.feature_columns).difference(features.columns)
        absent_prefixes = [
            channel_prefix(ch).replace(" ", "_") + "_"
            for ch in self.channels if ch not in config.channels
        ]
        if not set(self.channels[:2]).issubset(config.channels):
            absent_prefixes.append("inter_ratio_")
        if any(not col.startswith(tuple(absent_prefixes)) for col in missing):
            raise ValueError("Faltan características tabulares requeridas por DART.")
        aligned = features.reindex(
            columns=self.manifest.feature_columns, fill_value=0.0
        ).astype("float32")
        emg = self.channels[3]
        if emg in selected and emg not in config.channels:
            # Para EMG de envolvente a 1 Hz se conserva el valor ausente del entrenamiento DART.
            emg_prefix = channel_prefix(emg).replace(" ", "_") + "_"
            aligned.loc[:, aligned.columns.str.startswith(emg_prefix)] = np.nan
        return result, self.dart.predict(aligned, num_threads=4)

    def _neural(self, path, selected):
        features = spectral_input(path, self.channels, self.bands, selected_channels=selected)
        return crnn_probabilities(
            self.crnn, features, self.offsets, len(self.manifest.classes)
        )

    def _select_channels(self, path, requested):
        config = self.manifest.preprocessing
        with mne.io.read_raw_edf(path, preload=False, verbose="ERROR") as raw:
            available = set(raw.ch_names).intersection(self.channels)
            if raw.n_times / raw.info["sfreq"] < config.epoch_seconds:
                raise ValueError("Se requiere al menos una época completa de 30 s.")
        if requested is not None:
            if len(requested) != len(set(requested)):
                raise ValueError("La selección contiene canales repetidos.")
            unavailable = set(requested) - available
            if unavailable:
                names = ", ".join(sorted(unavailable))
                raise ValueError(f"Canales no disponibles para el modelo en este EDF: {names}.")
            available = set(requested)

        selected, tabular = [], []
        for ch in self.channels:
            if ch not in available:
                continue
            # MNE remuestrea al mayor ritmo al abrir varios canales. Comprobar cada ritmo nativo.
            with mne.io.read_raw_edf(path, include=[ch], verbose="ERROR") as signal:
                rate = signal.info["sfreq"]
            if rate == config.expected_sfreq:
                tabular.append(ch)
            elif ch != self.channels[3] or rate != 1:
                if requested is not None:
                    raise ValueError(f"Frecuencia incompatible para {ch}: {rate:g} Hz.")
                continue
            selected.append(ch)
        if not set(self.channels[:2]).intersection(selected):
            raise ValueError("Selecciona al menos un EEG a 100 Hz: EEG Fpz-Cz o EEG Pz-Oz.")
        return tuple(selected), replace(config, channels=tuple(tabular))

    def predict_edf(self, path, channels=None):
        try:
            selected, config = self._select_channels(path, channels)
            with self._lock, ThreadPoolExecutor(max_workers=1) as worker:
                neural = worker.submit(self._neural, path, selected)
                result, p_dart = self._tabular(path, config, selected)
                p_crnn = neural.result()
        except (OSError, RuntimeError, EOFError) as exc:
            raise ValueError(f"No fue posible procesar el EDF: {exc}") from exc
        if p_dart.shape != p_crnn.shape or p_dart.shape != (
            len(result.metadata),
            len(self.manifest.classes),
        ):
            raise ValueError("Las dos ramas devolvieron épocas o clases distintas.")
        probabilities = softmax(
            self.dart_weight * np.log(np.maximum(p_dart, self.floor))
            + self.crnn_weight * np.log(np.maximum(p_crnn, self.floor)),
            axis=1,
        )
        if not np.isfinite(probabilities).all():
            raise ValueError("Probabilidades de inferencia no finitas.")
        stages = tuple(
            np.asarray(self.manifest.classes)[probabilities.argmax(axis=1)].tolist()
        )
        return PredictionResult(
            stages,
            probabilities,
            result.metadata.onset_seconds.to_numpy(),
            result.metadata.duration_seconds.to_numpy(),
            result.sfreq,
            selected,
        )
