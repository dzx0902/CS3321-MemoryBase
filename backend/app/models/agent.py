from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AgentType = Literal["retriever", "editor", "reviewer", "exporter", "demo"]


class AgentRegisterRequest(BaseModel):
    workspace: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    agent_type: AgentType = "editor"


class AgentRegisterResponse(BaseModel):
    agent_id: UUID
    workspace_id: UUID
    name: str
    agent_type: AgentType
    status: str
