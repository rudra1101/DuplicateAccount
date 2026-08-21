from dataclasses import (
    asdict,
    dataclass,
    field,
)
from typing import Any


@dataclass(frozen=True)
class NormalizedAccount:
    account_id: str
    application: str
    username: str
    display_name: str
    first_name: str
    last_name: str
    email: str
    email_local_part: str
    email_domain: str
    employee_id: str
    department: str
    manager: str
    job_title: str
    phone: str
    location: str
    status: str
    created_at: str | None

    raw: dict[str, Any] = field(
        default_factory=dict,
        compare=False,
        repr=False,
    )

    def to_dict(
        self,
        *,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        result = asdict(self)
        if not include_raw:
            result.pop("raw", None)
        return result

    def original_id(self) -> str:
        possible_keys = (
            "id",
            "accountId",
            "account_id",
            "nativeIdentity",
            "native_identity",
        )
        for key in possible_keys:
            value = self.raw.get(key)
            if value is not None:
                return str(value)
        return self.account_id


@dataclass(frozen=True)
class ComparisonFeatures:
    username_similarity: float
    display_name_similarity: float
    first_name_similarity: float
    last_name_similarity: float
    email_similarity: float
    email_local_similarity: float
    manager_similarity: float
    department_similarity: float
    title_similarity: float
    location_similarity: float
    phone_similarity: float

    identity_embedding_similarity: float
    name_embedding_similarity: float
    organization_embedding_similarity: float

    employee_id_exact: bool
    email_exact: bool
    username_exact: bool
    phone_exact: bool
    department_exact: bool
    manager_exact: bool
    status_exact: bool
    same_application: bool

    account_1_missing_fields: int
    account_2_missing_fields: int

    # Evidence discovered from the application's actual source schema.
    dynamic_identifier_matches: int = 0
    dynamic_contact_matches: int = 0
    dynamic_name_matches: int = 0
    dynamic_org_matches: int = 0
    dynamic_unknown_matches: int = 0
    dynamic_identifier_conflicts: int = 0
    dynamic_matched_attributes: tuple[str, ...] = ()
    dynamic_conflicting_attributes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatchReason:
    field: str
    message: str
    impact: str
    similarity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DuplicatePrediction:
    account_1: NormalizedAccount
    account_2: NormalizedAccount
    confidence: float
    classification: str
    features: ComparisonFeatures
    reasons: list[MatchReason]
    warnings: list[MatchReason]
    model_version: str = "hybrid-embedding-v2"

    @property
    def account_1_id(self) -> str:
        return self.account_1.original_id()

    @property
    def account_2_id(self) -> str:
        return self.account_2.original_id()

    def to_dict(
        self,
        *,
        include_accounts: bool = True,
        include_raw_accounts: bool = False,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "account1Id": self.account_1_id,
            "account2Id": self.account_2_id,
            "confidence": self.confidence,
            "classification": self.classification,
            "modelVersion": self.model_version,
            "features": self.features.to_dict(),
            "reasons": [reason.to_dict() for reason in self.reasons],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

        if include_accounts:
            result["account1"] = self.account_1.to_dict(include_raw=include_raw_accounts)
            result["account2"] = self.account_2.to_dict(include_raw=include_raw_accounts)
        return result
