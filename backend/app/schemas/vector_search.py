from pydantic import (
    BaseModel,
    Field,
)


class VectorTextSearchRequest(BaseModel):
    query: str = Field(
        min_length=2,
        max_length=1000,
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    minimumSimilarity: float = Field(
        default=0.60,
        ge=-1.0,
        le=1.0,
    )

    scanId: int | None = Field(
        default=None,
        ge=1,
    )


class VectorAccountSearchRequest(BaseModel):
    application: str = ""
    username: str = ""
    displayName: str = ""
    email: str = ""
    employeeId: str = ""
    department: str = ""
    manager: str = ""
    status: str = ""
    jobTitle: str = ""
    location: str = ""
    phone: str = ""

    sourceAccountId: str | None = None

    excludeVectorId: int | None = Field(
        default=None,
        ge=1,
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    candidateLimit: int = Field(
        default=30,
        ge=1,
        le=200,
    )

    minimumSimilarity: float = Field(
        default=0.55,
        ge=-1.0,
        le=1.0,
    )

    minimumDuplicateConfidence: float = Field(
        default=50,
        ge=0,
        le=100,
    )

    scanId: int | None = Field(
        default=None,
        ge=1,
    )

    applicationFilter: str | None = None