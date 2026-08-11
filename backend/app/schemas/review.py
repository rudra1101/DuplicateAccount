from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


VALID_REVIEW_DECISIONS = {
    "DUPLICATE",
    "NOT_DUPLICATE",
    "UNCERTAIN",
}


class CandidateDecisionRequest(
    BaseModel
):
    decision: str = Field(
        min_length=1,
        max_length=30,
    )

    comment: str | None = Field(
        default=None,
        max_length=2000,
    )

    reviewerName: str | None = Field(
        default=None,
        max_length=255,
    )

    @field_validator("decision")
    @classmethod
    def validate_decision(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip().upper()

        if (
            normalized
            not in VALID_REVIEW_DECISIONS
        ):
            raise ValueError(
                "Decision must be DUPLICATE, "
                "NOT_DUPLICATE, or UNCERTAIN."
            )

        return normalized


class CandidateDecisionResponse(
    BaseModel
):
    candidateId: int
    decision: str
    comment: str | None
    reviewerName: str | None
    reviewedAt: str | None
    trainingLabelId: int
    labelSummary: dict