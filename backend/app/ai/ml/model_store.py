from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib


MODEL_DIRECTORY = (
    Path(__file__)
    .resolve()
    .parent
    / "models"
)

MODEL_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

DEFAULT_MODEL_PATH = (
    MODEL_DIRECTORY
    / "identity_match_model.joblib"
)


@dataclass
class StoredModel:
    model: Any
    metadata: dict[str, Any]


def save_model(
    model: Any,
    metadata: dict[str, Any],
    path: Path = DEFAULT_MODEL_PATH,
) -> None:
    payload = {
        "model": model,
        "metadata": metadata,
    }

    joblib.dump(
        payload,
        path,
    )


def load_model(
    path: Path = DEFAULT_MODEL_PATH,
) -> StoredModel | None:
    if not path.exists():
        return None

    payload = joblib.load(path)

    return StoredModel(
        model=payload["model"],
        metadata=payload.get(
            "metadata",
            {},
        ),
    )


def model_exists(
    path: Path = DEFAULT_MODEL_PATH,
) -> bool:
    return path.exists()