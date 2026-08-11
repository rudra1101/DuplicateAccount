from __future__ import annotations

from typing import Any

import numpy as np

from app.ai.ml.feature_vector import (
    features_to_vector,
)
from app.ai.ml.model_store import (
    load_model,
)


class DuplicateMLPredictor:
    def predict(
        self,
        features: dict[str, Any],
    ) -> tuple[
        float | None,
        str | None,
    ]:
        stored_model = load_model()

        if stored_model is None:
            return None, None

        vector = np.array(
            [
                features_to_vector(
                    features
                )
            ],
            dtype=float,
        )

        probability = float(
            stored_model.model.predict_proba(
                vector
            )[0][1]
        )

        model_version = (
            stored_model.metadata.get(
                "modelVersion"
            )
        )

        return (
            round(
                probability * 100,
                2,
            ),
            model_version,
        )


duplicate_ml_predictor = (
    DuplicateMLPredictor()
)