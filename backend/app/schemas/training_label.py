from pydantic import (
    BaseModel,
    Field,
)


class TrainingLabelCreate(BaseModel):
    candidateId: int = Field(
        ge=1,
    )

    label: str = Field(
        min_length=1,
        max_length=30,
    )

    reviewerComment: str | None = Field(
        default=None,
        max_length=2000,
    )

    reviewerName: str | None = Field(
        default=None,
        max_length=255,
    )