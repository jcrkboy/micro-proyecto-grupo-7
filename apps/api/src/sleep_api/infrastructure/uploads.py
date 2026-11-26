"""Repositorio local de archivos EDF y sus metadatos."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from threading import Lock
from time import time
from uuid import UUID, uuid4

from anyio import to_thread
from fastapi import UploadFile

from sleep_api.core.exceptions import UploadInUseError, UploadNotFoundError, UploadValidationError


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredUpload:
    upload_id: str
    patient_name: str
    original_filename: str
    size_bytes: int
    created_at: str
    file_path: Path


class LocalUploadRepository:
    """Almacena cargas por UUID; nunca usa el nombre original como ruta."""

    chunk_size = 1024 * 1024

    def __init__(self, root: Path, max_bytes: int, ttl_seconds: int) -> None:
        self.root = root
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self._active: set[str] = set()
        self._lock = Lock()
        self._cleanup_requested = asyncio.Event()
        self.root.mkdir(parents=True, exist_ok=True)

    def _delete_files(self, upload_id: str) -> None:
        for suffix in (".json", ".edf", ".part"):
            path = self.root / f"{upload_id}{suffix}"
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.exception("No se pudo eliminar %s. Se reintentará en la limpieza.", path.name)

    def remove_expired(self) -> None:
        cutoff = time() - self.ttl_seconds
        for path in self.root.iterdir():
            upload_id = path.stem
            if path.suffix not in {".edf", ".json", ".part"}:
                continue
            try:
                if str(UUID(upload_id)) != upload_id:
                    continue
            except ValueError:
                continue
            with self._lock:
                if upload_id in self._active:
                    continue
                try:
                    # El JSON se escribe al completar la carga. Si falta, queda un huérfano.
                    metadata_path = self._metadata_path(upload_id)
                    timestamp_path = metadata_path if metadata_path.is_file() else path
                    if timestamp_path.lstat().st_mtime <= cutoff:
                        self._delete_files(upload_id)
                except FileNotFoundError:
                    continue
                except OSError:
                    logger.exception("No se pudo revisar la carga %s", upload_id)

    async def run_cleanup(self) -> None:
        """Un único barrido al arrancar, tras las cargas y durante períodos sin tráfico."""
        while True:
            self._cleanup_requested.clear()
            try:
                await to_thread.run_sync(self.remove_expired)
            except OSError:
                logger.exception("No se pudo revisar el directorio de cargas")
            try:
                await asyncio.wait_for(self._cleanup_requested.wait(), min(60, self.ttl_seconds))
            except asyncio.TimeoutError:
                pass

    async def save(self, patient_name: str, upload: UploadFile) -> StoredUpload:
        patient_name = patient_name.strip()
        if not patient_name:
            raise UploadValidationError("El nombre de la persona es obligatorio")
        original_name = Path(upload.filename or "").name
        if Path(original_name).suffix.lower() != ".edf":
            raise UploadValidationError("Solo se aceptan archivos con extensión .edf")

        upload_id = str(uuid4())
        final_path = self.root / f"{upload_id}.edf"
        partial_path = self.root / f"{upload_id}.part"
        with self._lock:
            self._active.add(upload_id)
        try:
            size = 0
            with partial_path.open("xb") as destination:
                while chunk := await upload.read(self.chunk_size):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise UploadValidationError(
                            f"El archivo supera el límite de {self.max_bytes} bytes"
                        )
                    destination.write(chunk)
            if size == 0:
                raise UploadValidationError("El archivo EDF está vacío")
            with partial_path.open("rb") as source:
                if source.read(8) != b"0       ":
                    raise UploadValidationError(
                        "El contenido no tiene una cabecera EDF válida"
                    )
            partial_path.replace(final_path)
            stored = StoredUpload(
                upload_id=upload_id,
                patient_name=patient_name,
                original_filename=original_name,
                size_bytes=size,
                created_at=datetime.now(timezone.utc).isoformat(),
                file_path=final_path,
            )
            metadata = asdict(stored)
            metadata["file_path"] = str(final_path)
            self._metadata_path(upload_id).write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return stored
        except BaseException:
            self._delete_files(upload_id)
            raise
        finally:
            with self._lock:
                self._active.remove(upload_id)
            self._cleanup_requested.set()
            await upload.close()

    @contextmanager
    def consume(self, upload_id: str) -> Iterator[StoredUpload]:
        """Reserva el EDF antes de la cola y lo borra cuando el modelo deja de usarlo."""
        try:
            upload_id = str(UUID(upload_id))
        except ValueError:
            raise UploadNotFoundError("Identificador de carga no válido") from None

        with self._lock:
            if upload_id in self._active:
                raise UploadInUseError("Esta carga ya tiene un análisis en curso")
            stored = self._read(upload_id)
            self._active.add(upload_id)
        try:
            yield stored
        finally:
            with self._lock:
                self._delete_files(upload_id)
                self._active.remove(upload_id)

    def _read(self, upload_id: str) -> StoredUpload:
        metadata_path = self._metadata_path(upload_id)
        try:
            if metadata_path.stat().st_mtime <= time() - self.ttl_seconds:
                self._delete_files(upload_id)
                raise UploadNotFoundError("La carga caducó. Vuelve a subir el EDF")
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            raise UploadNotFoundError("No existe la carga solicitada") from None

        file_path = self.root / f"{upload_id}.edf"
        if not file_path.is_file():
            raise UploadNotFoundError("El archivo de la carga ya no está disponible")
        return StoredUpload(
            upload_id=upload_id,
            patient_name=str(payload["patient_name"]),
            original_filename=str(payload["original_filename"]),
            size_bytes=int(payload["size_bytes"]),
            created_at=str(payload["created_at"]),
            file_path=file_path,
        )

    def _metadata_path(self, upload_id: str) -> Path:
        return self.root / f"{upload_id}.json"
