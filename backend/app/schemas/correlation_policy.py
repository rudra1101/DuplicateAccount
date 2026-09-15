from pydantic import BaseModel, Field, field_validator


ALLOWED_MATCH_TYPES = {"EXACT", "CASE_INSENSITIVE", "NORMALIZED"}
ALLOWED_STRATEGIES = {"FIRST_MATCH_WINS"}


class CorrelationRuleInput(BaseModel):
    priority: int = Field(ge=1, le=100)
    accountAttribute: str = Field(min_length=1, max_length=255)
    identityAttribute: str = Field(min_length=1, max_length=255)
    matchType: str = "EXACT"
    enabled: bool = True

    @field_validator("accountAttribute", "identityAttribute")
    @classmethod
    def clean_attribute(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Correlation attribute cannot be empty.")
        return cleaned

    @field_validator("matchType")
    @classmethod
    def validate_match_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_MATCH_TYPES:
            raise ValueError(
                "matchType must be EXACT, CASE_INSENSITIVE, or NORMALIZED."
            )
        return normalized


class CorrelationPolicyInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    accountIntegrationId: int = Field(gt=0)
    authoritativeIntegrationId: int = Field(gt=0)
    strategy: str = "FIRST_MATCH_WINS"
    enabled: bool = True
    rules: list[CorrelationRuleInput] = Field(min_length=1)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_STRATEGIES:
            raise ValueError("Only FIRST_MATCH_WINS is supported currently.")
        return normalized


class CorrelationPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    authoritativeIntegrationId: int | None = Field(default=None, gt=0)
    strategy: str | None = None
    enabled: bool | None = None
    rules: list[CorrelationRuleInput] | None = None

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in ALLOWED_STRATEGIES:
            raise ValueError("Only FIRST_MATCH_WINS is supported currently.")
        return normalized
