from __future__ import annotations

from fastapi import FastAPI

from .api.agents import router as agents_router
from .api.governance import router as governance_router
from .api.health import router as health_router
from .api.memories import router as memories_router
from .api.observe import router as observe_router
from .api.recall import router as recall_router
from .api.sessions import router as sessions_router
from .api.sources import router as sources_router
from .api.wiki import router as wiki_router
from .core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(health_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")
    app.include_router(memories_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(observe_router, prefix="/api")
    app.include_router(recall_router, prefix="/api")
    app.include_router(wiki_router, prefix="/api")
    app.include_router(governance_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    return app


app = create_app()
