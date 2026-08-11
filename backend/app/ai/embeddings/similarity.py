from __future__ import annotations

import math


def cosine_similarity(
    vector_1: list[float],
    vector_2: list[float],
) -> float:
    if not vector_1 or not vector_2:
        return 0.0

    if len(vector_1) != len(
        vector_2
    ):
        raise ValueError(
            "Embedding vectors must have "
            "the same dimension."
        )

    dot_product = sum(
        value_1 * value_2
        for value_1, value_2 in zip(
            vector_1,
            vector_2,
            strict=True,
        )
    )

    norm_1 = math.sqrt(
        sum(
            value * value
            for value in vector_1
        )
    )

    norm_2 = math.sqrt(
        sum(
            value * value
            for value in vector_2
        )
    )

    if norm_1 == 0 or norm_2 == 0:
        return 0.0

    result = dot_product / (
        norm_1 * norm_2
    )

    return round(
        max(
            -1.0,
            min(
                result,
                1.0,
            ),
        ),
        6,
    )