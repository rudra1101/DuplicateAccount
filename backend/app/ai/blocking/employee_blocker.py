from __future__ import annotations

from typing import Any

from app.ai.blocking.normalizer import (
    normalize_identifier,
)


def build_employee_keys(
    employee_id: Any,
) -> set[str]:
    value = normalize_identifier(employee_id)

    if not value:
        return set()

    return {
        f"employee:exact:{value}",
    }
