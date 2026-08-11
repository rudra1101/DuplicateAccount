from __future__ import annotations

from typing import Any

from app.ai.blocking import (
    blocking_candidate_generator,
)


def detect_with_blocking(
    engine: Any,
    accounts: list[Any],
    *,
    minimum_confidence: float,
    include_embeddings: bool = True,
) -> list[Any]:
    predictions: list[Any] = []

    candidates = (
        blocking_candidate_generator
        .generate(accounts)
    )

    print(
        "[Blocking] "
        f"Accounts={len(accounts)}, "
        f"CandidatePairs={len(candidates)}"
    )

    for candidate in candidates:
        prediction = engine.compare(
            candidate.account_1,
            candidate.account_2,
            include_embeddings=(
                include_embeddings
            ),
        )

        if (
            prediction.confidence
            >= minimum_confidence
        ):
            predictions.append(
                prediction
            )

    return predictions
