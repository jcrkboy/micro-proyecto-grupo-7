"""Configuración de la API desde variables de entorno y archivo .env."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


API_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Valores operativos sin rutas personales incrustadas en el código."""

    app_name: str = "Sleep-EDFx API"
    api_version: str = "0.1.0"
    model_dir: Path = Path("../../data/models/sleep_staging_lightgbm_eeg_v2")
    upload_dir: Path = Path("storage/uploads")
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    cors_origins: list[str] = ["http://localhost:4200"]

    model_config = SettingsConfigDict(
        env_file=API_ROOT / ".env",
        env_prefix="SLEEP_API_",
        extra="ignore",
    )

    @field_validator("model_dir", "upload_dir", mode="after")
    @classmethod
    def resolve_relative_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = API_ROOT / value
        return value.expanduser().resolve()


def get_settings() -> Settings:
    return Settings()

