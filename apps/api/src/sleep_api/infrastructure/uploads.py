"""Repositorio local de archivos EDF y sus metadatos."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from sleep_api.core.exceptions import UploadNotFoundError, UploadValidationError


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

    def __init__(self, root: Path, max_bytes: int) -> None:
        self.root = root
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

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
        size = 0
        try:
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
        except Exception:
            partial_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

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

    def get(self, upload_id: str) -> StoredUpload:
        try:
            normalized_id = str(UUID(upload_id))
        except ValueError:
            raise UploadNotFoundError("Identificador de carga no válido") from None

        metadata_path = self._metadata_path(normalized_id)
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            raise UploadNotFoundError("No existe la carga solicitada") from None

        file_path = self.root / f"{normalized_id}.edf"
        if not file_path.is_file():
            raise UploadNotFoundError("El archivo de la carga ya no está disponible")
        return StoredUpload(
            upload_id=normalized_id,
            patient_name=str(payload["patient_name"]),
            original_filename=str(payload["original_filename"]),
            size_bytes=int(payload["size_bytes"]),
            created_at=str(payload["created_at"]),
            file_path=file_path,
        )

    def _metadata_path(self, upload_id: str) -> Path:
        return self.root / f"{upload_id}.json"
