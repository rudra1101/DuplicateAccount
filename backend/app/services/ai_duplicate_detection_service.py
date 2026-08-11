from typing import Any

from app.ai.duplicate_engine import (
    duplicate_detection_engine,
)
from app.ai.duplicate_engine.types import (
    DuplicatePrediction,
)


def detect_account_duplicates(
    accounts: list[dict[str, Any]],
    *,
    minimum_confidence: float = 70,
    cross_application_only: bool = False,
) -> list[DuplicatePrediction]:
    """
    Application-facing adapter for the new
    hybrid duplicate detection engine.

    The scan flow should call this service
    rather than importing the AI engine
    directly.
    """

    return duplicate_detection_engine.detect(
        accounts=accounts,
        minimum_confidence=(
            minimum_confidence
        ),
        cross_application_only=(
            cross_application_only
        ),
    )


def predictions_to_dicts(
    predictions: list[
        DuplicatePrediction
    ],
) -> list[dict[str, Any]]:
    return [
        prediction.to_dict(
            include_accounts=True,
            include_raw_accounts=False,
        )
        for prediction in predictions
    ]