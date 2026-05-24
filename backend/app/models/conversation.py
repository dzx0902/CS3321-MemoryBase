from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import PageResponse

SessionChannel = Literal["meeting", "chat", "import", "manual", "cli"]
SenderType = Literal["user", "agent", "system"]
MessageRole = Literal["user", "assistant", "system", "tool"]


class SessionCreateRequest(BaseModel):
    workspace_id: UUID
    agent_id: UUID | None = None
    started_by_user_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    channel: SessionChannel = "cli"


class SessionResponse(BaseModel):
    session_id: UUID
    workspace_id: UUID
    agent_id: UUID | None = None
    started_by_user_id: UUID | None = None
    title: str
    channel: SessionChannel
    started_at: datetime
    ended_at: datetime | None = None


class SessionListResponse(PageResponse[SessionResponse]):
    pass


class MessageCreateRequest(BaseModel):
    session_id: UUID
    sender_type: SenderType = "user"
    sender_id: UUID | None = None
    role: MessageRole
    content: str = Field(min_length=1)
    reply_to_message_id: UUID | None = None


class MessageResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    sender_type: SenderType
    sender_id: UUID | None = None
    role: MessageRole
    content: str
    created_at: datetime
    reply_to_message_id: UUID | None = None


class MessageBatchCreateRequest(BaseModel):
    messages: list[MessageCreateRequest] = Field(min_length=1, max_length=100)


class MessageBatchResponse(BaseModel):
    items: list[MessageResponse]
    total: int


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    limit: int
