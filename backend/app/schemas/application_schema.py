from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


ALLOWED_MATCH_TYPES = {"EXACT", "FUZZY", "CONTAINS", "NONE"}
ALLOWED_DORMANCY_DATE_FORMATS = {
    "AUTO",
    "ISO_8601",
    "UNIX_SECONDS",
    "UNIX_MILLISECONDS",
    "UNIX_MICROSECONDS",
    "UNIX_NANOSECONDS",
    "WINDOWS_FILETIME",
    "CUSTOM",
}
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
    nativeIdentityAttribute: str | None = None
    statusAttribute: str | None = None
    activeStatusValues: list[str] = Field(default_factory=list)
    inactiveStatusValues: list[str] = Field(default_factory=list)
    lastLoginAttribute: str | None = None
    lastLoginDateFormat: str = "AUTO"
    lastLoginCustomFormat: str | None = None
    inactivityThresholdDays: int | None = Field(default=None, ge=1, le=3650)
    attributes: list[SchemaAttributeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_application(self):
        self.name = self.name.strip()
        if self.displayName is not None:
            self.displayName = self.displayName.strip() or None
        if self.objectType is not None:
            self.objectType = self.objectType.strip() or None
        if self.nativeIdentityAttribute is not None:
            self.nativeIdentityAttribute = self.nativeIdentityAttribute.strip() or None
        if self.statusAttribute is not None:
            self.statusAttribute = self.statusAttribute.strip() or None
        if self.lastLoginAttribute is not None:
            self.lastLoginAttribute = self.lastLoginAttribute.strip() or None
        self.lastLoginDateFormat = (self.lastLoginDateFormat or "AUTO").strip().upper()
        if self.lastLoginCustomFormat is not None:
            self.lastLoginCustomFormat = self.lastLoginCustomFormat.strip() or None

        self.activeStatusValues = sorted(
            {str(value).strip() for value in self.activeStatusValues if str(value).strip()},
            key=str.casefold,
        )
        self.inactiveStatusValues = sorted(
            {str(value).strip() for value in self.inactiveStatusValues if str(value).strip()},
            key=str.casefold,
        )

        seen: set[str] = set()
        for attribute in self.attributes:
            key = attribute.name.lower()
            if key in seen:
                raise ValueError(f"Duplicate schema attribute: {attribute.name}")
            seen.add(key)

        if self.nativeIdentityAttribute is not None:
            if self.nativeIdentityAttribute.lower() not in seen:
                raise ValueError("Native identity attribute must exist in the application schema.")

        if self.statusAttribute is not None:
            if self.statusAttribute.lower() not in seen:
                raise ValueError("Status attribute must exist in the application schema.")
            active = {value.casefold() for value in self.activeStatusValues}
            inactive = {value.casefold() for value in self.inactiveStatusValues}
            if active.intersection(inactive):
                raise ValueError("Active and inactive status values cannot overlap.")

        if self.lastLoginAttribute is not None:
            if self.lastLoginAttribute.lower() not in seen:
                raise ValueError("Last-login attribute must exist in the application schema.")
            if self.lastLoginDateFormat not in ALLOWED_DORMANCY_DATE_FORMATS:
                raise ValueError("Unsupported last-login date format.")
            if self.lastLoginDateFormat == "CUSTOM" and not self.lastLoginCustomFormat:
                raise ValueError(
                    "A custom last-login date format is required when CUSTOM is selected."
                )
            if self.inactivityThresholdDays is None:
                raise ValueError(
                    "Inactivity threshold days are required when last-login tracking is enabled."
                )
        else:
            self.lastLoginDateFormat = "AUTO"
            self.lastLoginCustomFormat = None
            self.inactivityThresholdDays = None

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
