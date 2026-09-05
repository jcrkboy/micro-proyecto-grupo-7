"""Pipeline científico reutilizable para clasificación de etapas del sueño."""

from sleep_staging.config import PreprocessingConfig
from sleep_staging.inference import SleepStagePredictor
from sleep_staging.preprocessing import PreprocessingPipeline
from sleep_staging.types import PreprocessingResult

__all__ = [
    "PreprocessingConfig",
    "PreprocessingPipeline",
    "PreprocessingResult",
    "SleepStagePredictor",
]
__version__ = "0.1.0"
