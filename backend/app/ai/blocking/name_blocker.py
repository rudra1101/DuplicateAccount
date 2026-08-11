from __future__ import annotations

from typing import Any

from app.ai.blocking.normalizer import (
    normalize_identifier,
)


def build_name_keys(
    *,
    display_name: Any = None,
    first_name: Any = None,
    last_name: Any = None,
) -> set[str]:
    display = normalize_identifier(
        display_name
    )

    first = normalize_identifier(
        first_name
    )

    last = normalize_identifier(
        last_name
    )

    keys: set[str] = set()

    if display:
        keys.add(
            f"name:exact:{display}"
        )

        if len(display) >= 6:
            keys.add(
                f"name:prefix6:{display[:6]}"
            )

    if first and last:
        keys.add(
            f"name:first-last:{first}{last}"
        )

        keys.add(
            "name:first-initial-last:"
            f"{first[0]}{last}"
        )

    return keys
