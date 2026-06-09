from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.agents import router as agents_router
from .api.deps import get_graph_service
from .api.embeddings import router as embeddings_router
from .api.governance import router as governance_router
from .api.graph import router as graph_router
from .api.health import router as health_router
from .api.memories import router as memories_router
from .api.memory_extraction import router as memory_extraction_router
from .api.observe import router as observe_router
from .api.qa import router as qa_router
from .api.recall import router as recall_router
from .api.search import router as search_router
from .api.semantic import router as semantic_router
from .api.sessions import router as sessions_router
from .api.sources import router as sources_router
from .api.stats import router as stats_router
from .api.wiki import router as wiki_router
from .core.config import get_settings


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    try:
        yield
    finally:
        get_graph_service().close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=app_lifespan,
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")
    app.include_router(memories_router, prefix="/api")
    app.include_router(memory_extraction_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(observe_router, prefix="/api")
    app.include_router(qa_router, prefix="/api")
    app.include_router(recall_router, prefix="/api")
    app.include_router(search_router, prefix="/api")
    app.include_router(semantic_router, prefix="/api")
    app.include_router(wiki_router, prefix="/api")
    app.include_router(stats_router, prefix="/api")
    app.include_router(governance_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(graph_router, prefix="/api")
    app.include_router(embeddings_router, prefix="/api")
    return app


app = create_app()
