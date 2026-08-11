from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
)
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import (
    train_test_split,
)

from app.ai.ml.feature_vector import (
    FEATURE_NAMES,
    features_to_vector,
)
from app.ai.ml.model_store import (
    save_model,
)


VALID_TRAINING_LABELS = {
    "DUPLICATE": 1,
    "NOT_DUPLICATE": 0,
}


def train_duplicate_model(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    usable_rows = [
        row
        for row in rows
        if row.get("label")
        in VALID_TRAINING_LABELS
        and row.get("features")
    ]

    if len(usable_rows) < 20:
        raise ValueError(
            "At least 20 labelled examples are required."
        )

    y_values = [
        VALID_TRAINING_LABELS[
            row["label"]
        ]
        for row in usable_rows
    ]

    if len(set(y_values)) < 2:
        raise ValueError(
            "Training data must contain both "
            "DUPLICATE and NOT_DUPLICATE labels."
        )

    x_values = np.array(
        [
            features_to_vector(
                row["features"]
            )
            for row in usable_rows
        ],
        dtype=float,
    )

    y_array = np.array(
        y_values,
        dtype=int,
    )

    test_size = (
        0.25
        if len(usable_rows) >= 40
        else 0.20
    )

    x_train, x_test, y_train, y_test = (
        train_test_split(
            x_values,
            y_array,
            test_size=test_size,
            random_state=42,
            stratify=y_array,
        )
    )

    model = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=200,
        max_leaf_nodes=15,
        l2_regularization=0.2,
        random_state=42,
    )

    model.fit(
        x_train,
        y_train,
    )

    predictions = model.predict(
        x_test
    )

    probabilities = (
        model.predict_proba(
            x_test
        )[:, 1]
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            y_test,
            predictions,
            average="binary",
            zero_division=0,
        )
    )

    try:
        roc_auc = roc_auc_score(
            y_test,
            probabilities,
        )
    except ValueError:
        roc_auc = None

    model_version = (
        "identity-match-ml-v1-"
        + datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )
    )

    metadata = {
        "modelVersion": model_version,
        "trainedAt": datetime.now().isoformat(),
        "trainingRows": len(
            usable_rows
        ),
        "featureNames": FEATURE_NAMES,
        "metrics": {
            "accuracy": round(
                accuracy_score(
                    y_test,
                    predictions,
                ),
                4,
            ),
            "precision": round(
                precision,
                4,
            ),
            "recall": round(
                recall,
                4,
            ),
            "f1": round(
                f1,
                4,
            ),
            "rocAuc": (
                round(
                    roc_auc,
                    4,
                )
                if roc_auc is not None
                else None
            ),
        },
        "classificationReport": (
            classification_report(
                y_test,
                predictions,
                output_dict=True,
                zero_division=0,
            )
        ),
    }

    save_model(
        model=model,
        metadata=metadata,
    )

    return metadata