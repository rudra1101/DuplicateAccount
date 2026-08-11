from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VectorMetadata:
    vector_id: int
    scan_id: int | None
    source_account_id: str
    application: str
    username: str
    display_name: str
    email: str
    employee_id: str
    embedding_model: str
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
    ) -> "VectorMetadata":
        return cls(
            vector_id=int(value["vector_id"]),
            scan_id=(
                int(value["scan_id"])
                if value.get("scan_id") is not None
                else None
            ),
            source_account_id=str(
                value.get("source_account_id", "")
            ),
            application=str(
                value.get("application", "")
            ),
            username=str(
                value.get("username", "")
            ),
            display_name=str(
                value.get("display_name", "")
            ),
            email=str(
                value.get("email", "")
            ),
            employee_id=str(
                value.get("employee_id", "")
            ),
            embedding_model=str(
                value.get("embedding_model", "")
            ),
            extra=dict(
                value.get("extra", {})
            ),
        )


@dataclass(frozen=True)
class VectorSearchResult:
    score: float
    metadata: VectorMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "similarity": self.score,
            "account": self.metadata.to_dict(),
        }