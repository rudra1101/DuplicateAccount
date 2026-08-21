from typing import Any

from pydantic import BaseModel, Field


class Account(BaseModel):
    id: str | None = None

    application: str

    username: str

    displayName: str = ""

    email: str = ""

    employeeId: str | None = None

    department: str | None = None

    manager: str | None = None

    status: str | None = None

    created: str | None = None

    # Preserve the original source payload so schema-driven/AI matching can
    # evaluate attributes that are not part of the legacy account model.
    rawAttributes: dict[str, Any] = Field(default_factory=dict)
