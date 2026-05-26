from __future__ import annotations

from functools import lru_cache

from ..core.config import Settings, get_settings
from ..core.database import Database
from ..services.agent_service import AgentService, PostgresAgentRepository
from ..services.conversation_service import ConversationService, PostgresConversationRepository
from ..services.embedding_service import (
    EmbeddingService,
    LocalHashingEmbeddingProvider,
    PostgresEmbeddingRepository,
)
from ..services.governance_service import GovernanceService, PostgresGovernanceRepository
from ..services.memory_extraction_service import MemoryExtractionService
from ..services.memory_service import MemoryService, PostgresMemoryRepository
from ..services.recall_service import PostgresRecallRepository, RecallService
from ..services.search_service import PostgresSearchRepository, SearchService
from ..services.semantic_service import PostgresSemanticRepository, SemanticService
from ..services.source_service import PostgresSourceRepository, SourceService
from ..services.stats_service import PostgresStatsRepository, StatsService
from ..services.wiki_service import PostgresWikiRepository, WikiService


@lru_cache(maxsize=1)
def get_database() -> Database:
    settings = get_settings()
    return Database(settings.database_url)


def get_source_service() -> SourceService:
    settings = get_settings()
    repository = PostgresSourceRepository(get_database())
    return SourceService(
        repository=repository,
        chunk_max_chars=settings.chunk_max_chars,
        chunk_overlap_lines=settings.chunk_overlap_lines,
    )


def get_memory_service() -> MemoryService:
    repository = PostgresMemoryRepository(get_database())
    return MemoryService(repository=repository)


def get_memory_extraction_service() -> MemoryExtractionService:
    return MemoryExtractionService(
        database=get_database(),
        memory_service=get_memory_service(),
    )


def get_recall_service() -> RecallService:
    repository = PostgresRecallRepository(get_database())
    return RecallService(repository=repository)


def get_search_service() -> SearchService:
    repository = PostgresSearchRepository(get_database())
    return SearchService(repository=repository)


def get_semantic_service() -> SemanticService:
    repository = PostgresSemanticRepository(get_database())
    return SemanticService(repository=repository)


def get_governance_service() -> GovernanceService:
    repository = PostgresGovernanceRepository(get_database())
    return GovernanceService(repository=repository)


def get_agent_service() -> AgentService:
    repository = PostgresAgentRepository(get_database())
    return AgentService(repository=repository)


def get_conversation_service() -> ConversationService:
    repository = PostgresConversationRepository(get_database())
    return ConversationService(repository=repository)


def get_wiki_service() -> WikiService:
    repository = PostgresWikiRepository(get_database())
    return WikiService(repository=repository)


def get_stats_service() -> StatsService:
    repository = PostgresStatsRepository(get_database())
    return StatsService(repository=repository)


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(
        provider=LocalHashingEmbeddingProvider(),
        repository=PostgresEmbeddingRepository(get_database()),
    )


def get_app_settings() -> Settings:
    return get_settings()
