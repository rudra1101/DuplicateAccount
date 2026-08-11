from rapidfuzz import fuzz


def similarity_ratio(
    value_1: str,
    value_2: str,
) -> float:
    if not value_1 or not value_2:
        return 0.0

    return round(
        fuzz.ratio(
            value_1,
            value_2,
        ) / 100,
        4,
    )


def token_similarity(
    value_1: str,
    value_2: str,
) -> float:
    if not value_1 or not value_2:
        return 0.0

    ratio_score = fuzz.ratio(
        value_1,
        value_2,
    )

    token_sort_score = (
        fuzz.token_sort_ratio(
            value_1,
            value_2,
        )
    )

    token_set_score = (
        fuzz.token_set_ratio(
            value_1,
            value_2,
        )
    )

    return round(
        max(
            ratio_score,
            token_sort_score,
            token_set_score,
        ) / 100,
        4,
    )


def username_similarity(
    username_1: str,
    username_2: str,
) -> float:
    if not username_1 or not username_2:
        return 0.0

    scores = [
        fuzz.ratio(
            username_1,
            username_2,
        ),
        fuzz.partial_ratio(
            username_1,
            username_2,
        ),
    ]

    compact_1 = username_1.replace(
        ".",
        "",
    ).replace(
        "_",
        "",
    ).replace(
        "-",
        "",
    )

    compact_2 = username_2.replace(
        ".",
        "",
    ).replace(
        "_",
        "",
    ).replace(
        "-",
        "",
    )

    scores.append(
        fuzz.ratio(
            compact_1,
            compact_2,
        )
    )

    return round(
        max(scores) / 100,
        4,
    )


def exact_match(
    value_1: str,
    value_2: str,
) -> bool:
    return bool(
        value_1
        and value_2
        and value_1 == value_2
    )