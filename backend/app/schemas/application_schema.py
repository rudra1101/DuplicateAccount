from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


ALLOWED_MATCH_TYPES = {"EXACT", "FUZZY", "CONTAINS", "NONE"}
ALLOWED_NORMALIZATIONS = {
    "NONE",
    "TRIM",
    "LOWERCASE",
    "UPPERCASE",
    "ALPHANUMERIC",
    "EMAIL",
    "PHONE",
    "NAME",
}


class SchemaAttributeInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    displayName: str | None = None
    dataType: str = "string"
    required: bool = False
    multiValued: bool = False
    position: int = 0
    useForMatching: bool = False
    matchType: str | None = None
    matchWeight: float = Field(default=0.0, ge=0.0, le=100.0)
    normalizationType: str | None = None

    @model_validator(mode="after")
    def validate_matching(self):
        if self.useForMatching:
            match_type = (self.matchType or "EXACT").upper()
            if match_type not in ALLOWED_MATCH_TYPES - {"NONE"}:
                raise ValueError("Matching attributes require a valid match type.")
            self.matchType = match_type
        else:
            self.matchType = "NONE"
            self.matchWeight = 0.0

        normalization = (self.normalizationType or "NONE").upper()
        if normalization not in ALLOWED_NORMALIZATIONS:
            raise ValueError("Unsupported normalization type.")
        self.normalizationType = normalization
        self.dataType = self.dataType.strip().lower() or "string"
        self.name = self.name.strip()
        if self.displayName is not None:
            self.displayName = self.displayName.strip() or None
        return self


class ApplicationInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    displayName: str | None = None
    objectType: str | None = None
    enabled: bool = True
    schemaName: str | None = None
    attributes: list[SchemaAttributeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_application(self):
        self.name = self.name.strip()
        if self.displayName is not None:
            self.displayName = self.displayName.strip() or None
        if self.objectType is not None:
            self.objectType = self.objectType.strip() or None

        seen: set[str] = set()
        for attribute in self.attributes:
            key = attribute.name.lower()
            if key in seen:
                raise ValueError(f"Duplicate schema attribute: {attribute.name}")
            seen.add(key)

        total_weight = sum(
            attribute.matchWeight
            for attribute in self.attributes
            if attribute.useForMatching
        )
        if total_weight > 100.0001:
            raise ValueError("Matching weights cannot total more than 100.")
        return self


class IntegrationApplicationsPayload(BaseModel):
    applications: list[ApplicationInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_names(self):
        names = [item.name.lower() for item in self.applications]
        if len(names) != len(set(names)):
            raise ValueError("Application names must be unique within an integration.")
        return self
