from __future__ import annotations

from typing import Any

from app.ai.blocking.normalizer import (
    normalize_email,
    normalize_email_local_part,
)


def build_email_keys(
    email: Any,
) -> set[str]:
    normalized = normalize_email(email)

    if not normalized:
        return set()

    keys = {
        f"email:exact:{normalized}",
    }

    local_part = normalize_email_local_part(
        normalized
    )

    if local_part:
        keys.add(
            f"email:local:{local_part}"
        )

        if len(local_part) >= 6:
            keys.add(
                "email:local-prefix6:"
                f"{local_part[:6]}"
            )

    return keys
