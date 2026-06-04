from __future__ import annotations

from functools import lru_cache

from ..core.config import Settings, get_settings
from ..core.database import Database
from ..services.agent_service import AgentService, PostgresAgentRepository
from ..services.conversation_service import ConversationService, PostgresConversationRepository
from ..services.embedding_service import (
    EmbeddingProvider,
    EmbeddingService,
    LocalHashingEmbeddingProvider,
    PostgresEmbeddingRepository,
    SiliconFlowEmbeddingProvider,
)
from ..services.governance_service import GovernanceService, PostgresGovernanceRepository
from ..services.graph_service import (
    GraphService,
    Neo4jGraphStore,
    PostgresGraphRepository,
    PostgresGraphVisibilityRepository,
)
from ..services.llm_service import AnswerService, ChatProvider, OpenAICompatibleChatProvider
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
    settings = get_settings()
    repository = _build_recall_repository(settings)
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


@lru_cache(maxsize=1)
def get_graph_service() -> GraphService:
    repository = PostgresGraphRepository(get_database())
    visibility_repository = PostgresGraphVisibilityRepository(get_database())
    store = Neo4jGraphStore(get_settings())
    return GraphService(
        repository=repository,
        store=store,
        visibility_repository=visibility_repository,
    )


def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(
        provider=_build_embedding_provider(settings),
        repository=PostgresEmbeddingRepository(get_database()),
        default_provider_name=_embedding_provider_name(settings),
        default_model=_embedding_model(settings),
        default_dimension=_embedding_dimension(settings),
    )


def get_answer_service() -> AnswerService:
    settings = get_settings()
    return AnswerService(
        recall_service=RecallService(repository=_build_recall_repository(settings)),
        chat_provider=_build_chat_provider(settings),
        default_temperature=settings.llm_temperature,
        default_max_tokens=settings.llm_max_tokens,
    )


def get_app_settings() -> Settings:
    return get_settings()


def _build_recall_repository(settings: Settings) -> PostgresRecallRepository:
    return PostgresRecallRepository(
        get_database(),
        embedding_provider=_build_embedding_provider(settings),
        embedding_provider_name=_embedding_provider_name(settings),
        embedding_model=_embedding_model(settings),
        embedding_dimension=_embedding_dimension(settings),
    )


def _build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = _embedding_provider_name(settings)
    if provider == "siliconflow":
        return SiliconFlowEmbeddingProvider(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
        )
    if provider == "local":
        return LocalHashingEmbeddingProvider()
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


def _embedding_provider_name(settings: Settings) -> str:
    return settings.embedding_provider.strip().lower() or "local"


def _embedding_model(settings: Settings) -> str:
    if _embedding_provider_name(settings) == "siliconflow":
        return settings.siliconflow_embedding_model
    return "hashing-v1"


def _embedding_dimension(settings: Settings) -> int:
    if _embedding_provider_name(settings) == "siliconflow":
        return settings.siliconflow_embedding_dimensions
    return 128


def _build_chat_provider(settings: Settings) -> ChatProvider:
    provider = _llm_provider_name(settings)
    if provider == "deepseek":
        return OpenAICompatibleChatProvider(
            provider_name="deepseek",
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_chat_model,
        )
    if provider == "siliconflow":
        return OpenAICompatibleChatProvider(
            provider_name="siliconflow",
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            model=settings.siliconflow_chat_model,
        )
    raise ValueError("LLM_PROVIDER must be configured as 'deepseek' or 'siliconflow' for QA.")


def _llm_provider_name(settings: Settings) -> str:
    provider = settings.llm_provider.strip().lower()
    if provider:
        return provider
    if settings.deepseek_api_key:
        return "deepseek"
    if settings.siliconflow_api_key and settings.siliconflow_chat_model:
        return "siliconflow"
    return ""
