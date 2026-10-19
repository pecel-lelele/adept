"""FastAPI entry point.

Feature routers are auto-discovered: any `app/features/<name>/router.py` that
exposes `router` is mounted under /api/v1. Nobody edits this file to add routes.
"""

import importlib
import pkgutil

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app import features
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.routes import router as core_router

log = get_logger("app")


def discover_feature_routers() -> list[tuple[str, APIRouter]]:
    found: list[tuple[str, APIRouter]] = []
    for mod in sorted(pkgutil.iter_modules(features.__path__), key=lambda m: m.name):
        if not mod.ispkg:
            continue
        module_name = f"{features.__name__}.{mod.name}.router"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            found.append((mod.name, router))
    return found


def _operation_id(route: APIRoute) -> str:
    tag = str(route.tags[0]) if route.tags else "default"
    return f"{tag}_{route.name}"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        separate_input_output_schemas=False,
        generate_unique_id_function=_operation_id,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(core_router, prefix=settings.api_prefix)
    for name, router in discover_feature_routers():
        app.include_router(router, prefix=settings.api_prefix)
        log.debug("mounted feature router: %s", name)
    return app


app = create_app()
