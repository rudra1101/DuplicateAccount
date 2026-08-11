from __future__ import annotations

from typing import Any

from app.ai.blocking.normalizer import (
    normalize_identifier,
)


def build_username_keys(
    username: Any,
) -> set[str]:
    value = normalize_identifier(username)

    if not value:
        return set()

    keys = {
        f"username:exact:{value}",
    }

    if len(value) >= 6:
        keys.add(
            f"username:prefix6:{value[:6]}"
        )

    if len(value) >= 4:
        keys.add(
            f"username:suffix4:{value[-4:]}"
        )

    return keys
