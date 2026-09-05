from fastapi import APIRouter

from sleep_api.api.routes import health, predictions, uploads


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(uploads.router)
api_router.include_router(predictions.router)

