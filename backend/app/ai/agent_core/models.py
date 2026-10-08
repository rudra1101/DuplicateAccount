from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    SOURCE_ACCOUNT = "SOURCE_ACCOUNT"
    IDENTITY = "IDENTITY"
    INTEGRATION = "INTEGRATION"
    DUPLICATE_GROUP = "DUPLICATE_GROUP"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    REMEDIATION_ITEM = "REMEDIATION_ITEM"
    EXECUTION = "EXECUTION"
    REPORT = "REPORT"


class AgentEntity(BaseModel):
    entity_type: EntityType
    id: int | str | None = None
    label: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None


class PendingAction(BaseModel):
    capability: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Structured state carried by Rudrix across an agent run.

    This intentionally stores product entities rather than raw natural-language
    assumptions. The state can later be persisted per conversation without
    changing the planner/tool contracts.
    """

    current_account: AgentEntity | None = None
    current_identity: AgentEntity | None = None
    current_integration: AgentEntity | None = None
    current_duplicate_group: AgentEntity | None = None
    current_duplicate_candidate: AgentEntity | None = None
    current_remediation_item: AgentEntity | None = None
    current_execution: AgentEntity | None = None
    last_filters: dict[str, Any] = Field(default_factory=dict)
    pending_action: PendingAction | None = None

    def compact(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class CapabilityKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    NAVIGATION = "NAVIGATION"
    KNOWLEDGE = "KNOWLEDGE"


class AgentCapability(BaseModel):
    name: str
    domain: str
    kind: CapabilityKind
    description: str
    required_permission: str | None = None
    destructive: bool = False
    fast_path: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)
