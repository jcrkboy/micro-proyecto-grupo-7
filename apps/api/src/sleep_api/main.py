"""Punto de entrada ASGI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sleep_api.api.routes.health import health
from sleep_api.api.routes.predictions import infer
from sleep_api.api.router import api_router
from sleep_api.core.config import Settings, get_settings
from sleep_api.lifespan import lifespan
from sleep_api.schemas.health import HealthResponse
from sleep_api.schemas.predictions import InferenceResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    application = FastAPI(
        title=config.app_name,
        version=config.api_version,
        lifespan=lifespan,
    )
    application.state.settings = config
    application.include_router(api_router, prefix="/api/v1")

    # Alias directos requeridos; el frontend debe usar las rutas versionadas.
    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        response_model=HealthResponse,
        include_in_schema=False,
    )
    application.add_api_route(
        "/inferencia",
        infer,
        methods=["POST"],
        response_model=InferenceResponse,
        include_in_schema=False,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    return application


app = create_app()
