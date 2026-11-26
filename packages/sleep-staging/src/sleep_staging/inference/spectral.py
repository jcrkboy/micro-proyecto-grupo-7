"""Receta espectral contextual v1 del modelo mixto."""

from pathlib import Path
import mne
import numpy as np
from scipy.fft import rfft
from scipy.ndimage import convolve1d
from scipy.special import softmax


def spectral_input(archivo_edf, channels, bands, *, selected_channels=None):
    """Representación de una noche en seis bloques espectrales por época."""
    archivo_edf = Path(archivo_edf)
    requested = channels if selected_channels is None else selected_channels
    with mne.io.read_raw_edf(
        archivo_edf, include=list(requested), preload=True, verbose="ERROR"
    ) as raw:
        if raw.info["sfreq"] != 100:
            raise ValueError("La CRNN requiere una señal a 100 Hz.")
        presentes = [c for c in requested if c in raw.ch_names]
        required = channels[:3] if selected_channels is None else selected_channels
        if not set(required).issubset(presentes):
            raise ValueError(f"Faltan señales EEG/EOG en {archivo_edf.name}")
        raw.pick(presentes).filter(0.3, 35.0, verbose=False)
        n = raw.n_times // 3000
        signal = np.empty((n, 3000, len(presentes)), dtype="float32")
        for j, ch in enumerate(presentes):
            v = raw.get_data(picks=[ch], stop=n * 3000).reshape(n, 3000) * 1e6
            signal[:, :, j] = (v - v.mean(1, keepdims=True)) / (
                v.std(1, keepdims=True) + 1e-8
            )
    f = np.fft.rfftfreq(500, 1 / 100)
    ventana = np.hanning(500).astype("float32")[None, None, :, None]
    slots = [
        band * len(channels) + channels.index(ch)
        for band in range(len(bands))
        for ch in presentes
    ]
    x = np.zeros((n, 6, len(bands) * len(channels)), dtype="float32")
    for i in range(0, n, 100):
        bloque = signal[i : i + 100].reshape(-1, 6, 500, len(presentes))
        potencia = np.abs(rfft(bloque * ventana, axis=2)) ** 2 / 500
        x[i : i + len(bloque), :, slots] = np.concatenate(
            [
                np.log1p(potencia[:, :, (f >= a) & (f < b)].mean(axis=2))
                for a, b in bands
            ],
            axis=-1,
        )
    q10, mediana, q90 = np.percentile(x.reshape(-1, 24), [10, 50, 90], axis=0)
    z = np.clip((x - mediana) / np.maximum(q90 - q10, 0.05), -5, 5).astype("float32")
    media = z.mean(axis=1)
    triangular = np.r_[1:9, 7:0:-1].astype("float32")
    centro = convolve1d(media, triangular / triangular.sum(), axis=0, mode="nearest")
    pad = np.pad(media, ((3, 0), (0, 0)), mode="edge")
    pasado = sum(pad[i : i + n] for i in range(4)) / 4
    return np.concatenate(
        [
            x,
            z,
            np.broadcast_to(centro[:, None], x.shape),
            np.broadcast_to(pasado[:, None], x.shape),
        ],
        axis=-1,
    )


def bloques(x, desfase, relleno=0):
    pad = [(desfase, -(len(x) + desfase) % 15)] + [(0, 0)] * (x.ndim - 1)
    return np.pad(x, pad, constant_values=relleno).reshape(-1, 15, *x.shape[1:])


def crnn_probabilities(red, x, offsets, n_classes, *, check_cancelled=None):
    """Media geométrica de las probabilidades de las tres ventanas solapadas."""
    vistas = []
    for d in offsets:
        if check_cancelled:
            check_cancelled()
        v = red.predict(bloques(x, d), batch_size=128, verbose=0).reshape(-1, n_classes)
        vistas.append(v[d : d + len(x)].astype("float64"))
    return softmax(np.log(np.maximum(vistas, 1e-10)).mean(axis=0), axis=1)
