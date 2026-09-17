from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SourcePurpose = Literal["ACCOUNT", "AUTHORITATIVE"]


class IntegrationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    connectorType: str = Field(min_length=2, max_length=50)
    sourcePurpose: SourcePurpose = "ACCOUNT"
    description: str | None = Field(default=None, max_length=1000)
    configuration: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    sourcePurpose: SourcePurpose | None = None
    description: str | None = Field(default=None, max_length=1000)
    configuration: dict[str, Any] | None = None
    enabled: bool | None = None


class SchemaDetectionRequest(BaseModel):
    connectorType: str = Field(min_length=2, max_length=50)
    configuration: dict[str, Any] = Field(default_factory=dict)


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    connectorType: str
    sourcePurpose: SourcePurpose
    description: str | None
    configuration: dict[str, Any]
    enabled: bool
    createdAt: datetime
    updatedAt: datetime
