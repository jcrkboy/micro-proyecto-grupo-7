"""Exportación del bundle mixto y trazabilidad de entrenamiento fuera del servicio."""

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4


@contextmanager
def stage_mixed_bundle(destination):
    """Prepara ambos pesos y su manifiesto juntos antes de reemplazar el ajuste anterior."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temporary:
        work = Path(temporary)
        ready = work / "nuevo"
        ready.mkdir()
        yield ready
        if set(file.name for file in ready.iterdir()) != {"dart.txt", "crnn.keras", "manifest.json"}:
            raise ValueError("La exportación del modelo mixto está incompleta.")
        previous = work / "anterior"
        if destination.exists():
            destination.rename(previous)
        try:
            ready.rename(destination)
        except OSError:
            if previous.exists() and not destination.exists():
                previous.rename(destination)
            raise


def compact_manifest(info, training_hash):
    contract = info["contrato"]
    profiles = contract["preprocesamiento_dart"]
    common = dict(profiles["Telemetry"])
    channels = common.pop("channels")
    if profiles["Cassette"] != {**common, "channels": channels[:3]}:
        raise ValueError(
            "Los perfiles de ambas cohortes deben coincidir salvo por el EMG."
        )
    return {
        "artifact_version": 2,
        "model_type": "LightGBM DART + CRNN",
        "version": info["version_experimento"],
        "personas": len(contract["personas_entrenamiento"]),
        "clases": contract["clases"],
        "archivos": info["archivos"],
        "fusion": contract["fusion"],
        "canales": channels,
        "preprocesamiento_dart": common,
        "receta_crnn": "espectral-contextual-v1",
        "bandas_hz": contract["bandas_hz"],
        "desfases": contract["desfases"],
        "entrenamiento_sha256": training_hash,
    }


def _write_atomic(path, content):
    temp = path.with_name(uuid4().hex + ".tmp")
    try:
        temp.write_bytes(content)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def save_mixed_manifest(path, experiment, info):
    """Publica el manifiesto una vez disponibles sus pesos y la ficha de entrenamiento."""
    metadata = Path(experiment) / "entrenamiento"
    metadata.mkdir(parents=True, exist_ok=True)
    content = json.dumps(info, ensure_ascii=False, indent=2).encode("utf8")
    digest = hashlib.sha256(content).hexdigest()
    _write_atomic(metadata / (digest + ".json"), content)
    compact = compact_manifest(info, digest)
    _write_atomic(
        Path(path), (json.dumps(compact, ensure_ascii=False, indent=2) + "\n").encode()
    )


def read_training_manifest(path, experiment):
    """Carga la ficha completa para reproducir el ajuste o auditar la partición."""
    compact = json.loads(Path(path).read_bytes())
    digest = compact["entrenamiento_sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Huella de la ficha de entrenamiento inválida.")
    content = (Path(experiment) / "entrenamiento" / (digest + ".json")).read_bytes()
    info = json.loads(content)
    if (
        hashlib.sha256(content).hexdigest() != digest
        or compact_manifest(info, digest) != compact
    ):
        raise ValueError("El manifiesto no corresponde a la ficha de entrenamiento.")
    return info
