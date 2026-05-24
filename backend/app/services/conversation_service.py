from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.conversation import (
    MessageBatchCreateRequest,
    MessageBatchResponse,
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
)


class ConversationNotFoundError(Exception):
    pass


class ConversationValidationError(Exception):
    pass


class ConversationRepository(Protocol):
    def create_session(self, payload: SessionCreateRequest) -> SessionResponse:
        ...

    def list_sessions(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID | None,
        page: int,
        page_size: int,
    ) -> SessionListResponse:
        ...

    def get_session(self, session_id: UUID, workspace_id: UUID | None) -> SessionResponse | None:
        ...

    def list_messages(
        self,
        *,
        session_id: UUID,
        workspace_id: UUID | None,
        limit: int,
    ) -> MessageListResponse:
        ...

    def create_message(self, payload: MessageCreateRequest) -> MessageResponse:
        ...

    def create_messages(self, payload: MessageBatchCreateRequest) -> MessageBatchResponse:
        ...


@dataclass(slots=True)
class ConversationService:
    repository: ConversationRepository

    def create_session(self, payload: SessionCreateRequest) -> SessionResponse:
        return self.repository.create_session(payload)

    def list_sessions(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID | None,
        page: int,
        page_size: int,
    ) -> SessionListResponse:
        return self.repository.list_sessions(
            workspace_id=workspace_id,
            agent_id=agent_id,
            page=page,
            page_size=page_size,
        )

    def get_session(self, session_id: UUID, workspace_id: UUID | None) -> SessionResponse:
        session = self.repository.get_session(session_id, workspace_id)
        if session is None:
            raise ConversationNotFoundError(f"session {session_id} not found")
        return session

    def list_messages(
        self,
        *,
        session_id: UUID,
        workspace_id: UUID | None,
        limit: int,
    ) -> MessageListResponse:
        return self.repository.list_messages(
            session_id=session_id,
            workspace_id=workspace_id,
            limit=limit,
        )

    def create_message(self, payload: MessageCreateRequest) -> MessageResponse:
        return self.repository.create_message(payload)

    def create_messages(self, payload: MessageBatchCreateRequest) -> MessageBatchResponse:
        return self.repository.create_messages(payload)


class PostgresConversationRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create_session(self, payload: SessionCreateRequest) -> SessionResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                self._validate_workspace(cur, payload.workspace_id)
                if payload.agent_id is not None:
                    self._validate_agent(cur, payload.workspace_id, payload.agent_id)
                cur.execute(
                    """
                    INSERT INTO agent_session (
                        workspace_id,
                        agent_id,
                        started_by_user_id,
                        title,
                        channel
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(agent_id)s,
                        %(started_by_user_id)s,
                        %(title)s,
                        %(channel)s
                    )
                    RETURNING
                        session_id,
                        workspace_id,
                        agent_id,
                        started_by_user_id,
                        title,
                        channel,
                        started_at,
                        ended_at
                    """,
                    payload.model_dump(),
                )
                row = cur.fetchone()
            conn.commit()
        return SessionResponse(**row)

    def list_sessions(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID | None,
        page: int,
        page_size: int,
    ) -> SessionListResponse:
        filters = ["workspace_id = %(workspace_id)s"]
        params: dict[str, object] = {
            "workspace_id": workspace_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if agent_id is not None:
            filters.append("agent_id = %(agent_id)s")
            params["agent_id"] = agent_id
        where_clause = " AND ".join(filters)
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                self._validate_workspace(cur, workspace_id)
                cur.execute(
                    f"SELECT count(*) AS total FROM agent_session WHERE {where_clause}",
                    params,
                )
                total = cur.fetchone()["total"]
                cur.execute(
                    f"""
                    SELECT
                        session_id,
                        workspace_id,
                        agent_id,
                        started_by_user_id,
                        title,
                        channel,
                        started_at,
                        ended_at
                    FROM agent_session
                    WHERE {where_clause}
                    ORDER BY started_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = cur.fetchall()
        return SessionListResponse(
            items=[SessionResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_session(self, session_id: UUID, workspace_id: UUID | None) -> SessionResponse | None:
        filters = ["session_id = %(session_id)s"]
        params: dict[str, object] = {"session_id": session_id}
        if workspace_id is not None:
            filters.append("workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        session_id,
                        workspace_id,
                        agent_id,
                        started_by_user_id,
                        title,
                        channel,
                        started_at,
                        ended_at
                    FROM agent_session
                    WHERE {' AND '.join(filters)}
                    """,
                    params,
                )
                row = cur.fetchone()
        return SessionResponse(**row) if row else None

    def list_messages(
        self,
        *,
        session_id: UUID,
        workspace_id: UUID | None,
        limit: int,
    ) -> MessageListResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                session = self.get_session(session_id, workspace_id)
                if session is None:
                    raise ConversationNotFoundError(f"session {session_id} not found")
                cur.execute(
                    """
                    SELECT count(*) AS total
                    FROM message
                    WHERE session_id = %(session_id)s
                    """,
                    {"session_id": session_id},
                )
                total = cur.fetchone()["total"]
                cur.execute(
                    """
                    SELECT
                        message_id,
                        session_id,
                        sender_type,
                        sender_id,
                        role,
                        content,
                        created_at,
                        reply_to_message_id
                    FROM message
                    WHERE session_id = %(session_id)s
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                    """,
                    {"session_id": session_id, "limit": limit},
                )
                rows = list(reversed(cur.fetchall()))
        return MessageListResponse(
            items=[MessageResponse(**row) for row in rows],
            total=total,
            limit=limit,
        )

    def create_message(self, payload: MessageCreateRequest) -> MessageResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                row = self._insert_message(cur, payload)
            conn.commit()
        return MessageResponse(**row)

    def create_messages(self, payload: MessageBatchCreateRequest) -> MessageBatchResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                rows = [self._insert_message(cur, message) for message in payload.messages]
            conn.commit()
        return MessageBatchResponse(
            items=[MessageResponse(**row) for row in rows],
            total=len(rows),
        )

    def _insert_message(self, cur, payload: MessageCreateRequest) -> dict[str, object]:
        self._validate_session(cur, payload.session_id)
        if payload.reply_to_message_id is not None:
            self._validate_reply_message(cur, payload.session_id, payload.reply_to_message_id)
        cur.execute(
            """
            INSERT INTO message (
                session_id,
                sender_type,
                sender_id,
                role,
                content,
                reply_to_message_id
            )
            VALUES (
                %(session_id)s,
                %(sender_type)s,
                %(sender_id)s,
                %(role)s,
                %(content)s,
                %(reply_to_message_id)s
            )
            RETURNING
                message_id,
                session_id,
                sender_type,
                sender_id,
                role,
                content,
                created_at,
                reply_to_message_id
            """,
            payload.model_dump(),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("failed to create message")
        return row

    def _validate_workspace(self, cur, workspace_id: UUID) -> None:
        cur.execute(
            "SELECT 1 FROM workspace WHERE workspace_id = %(workspace_id)s",
            {"workspace_id": workspace_id},
        )
        if cur.fetchone() is None:
            raise ConversationNotFoundError(f"workspace {workspace_id} not found")

    def _validate_agent(self, cur, workspace_id: UUID, agent_id: UUID) -> None:
        cur.execute(
            """
            SELECT 1
            FROM agent
            WHERE agent_id = %(agent_id)s
              AND workspace_id = %(workspace_id)s
            """,
            {"agent_id": agent_id, "workspace_id": workspace_id},
        )
        if cur.fetchone() is None:
            raise ConversationValidationError(
                f"agent {agent_id} does not belong to workspace {workspace_id}"
            )

    def _validate_session(self, cur, session_id: UUID) -> None:
        cur.execute(
            "SELECT 1 FROM agent_session WHERE session_id = %(session_id)s",
            {"session_id": session_id},
        )
        if cur.fetchone() is None:
            raise ConversationNotFoundError(f"session {session_id} not found")

    def _validate_reply_message(self, cur, session_id: UUID, reply_to_message_id: UUID) -> None:
        cur.execute(
            """
            SELECT 1
            FROM message
            WHERE message_id = %(reply_to_message_id)s
              AND session_id = %(session_id)s
            """,
            {"reply_to_message_id": reply_to_message_id, "session_id": session_id},
        )
        if cur.fetchone() is None:
            raise ConversationValidationError(
                f"reply message {reply_to_message_id} does not belong to session {session_id}"
            )
