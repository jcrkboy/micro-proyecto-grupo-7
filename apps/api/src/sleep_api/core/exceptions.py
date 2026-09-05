"""Errores de dominio que las rutas convierten a HTTP."""


class UploadNotFoundError(LookupError):
    """El identificador no corresponde a una carga persistida."""


class UploadValidationError(ValueError):
    """El archivo no cumple el contrato de carga."""


class ModelUnavailableError(RuntimeError):
    """No hay un bundle cargado para ejecutar inferencia."""

