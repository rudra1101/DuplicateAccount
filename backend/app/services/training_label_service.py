from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_models.duplicate_candidate import (
    DuplicateCandidateRecord,
)
from app.db_models.duplicate_training_label import (
    DuplicateTrainingLabelRecord,
)


VALID_LABELS = {
    "DUPLICATE",
    "NOT_DUPLICATE",
    "UNCERTAIN",
}


def normalize_training_label(
    label: str,
) -> str:
    normalized = str(
        label or ""
    ).strip().upper()

    if normalized not in VALID_LABELS:
        raise ValueError(
            "Label must be DUPLICATE, "
            "NOT_DUPLICATE, or UNCERTAIN."
        )

    return normalized


def create_training_label(
    db: Session,
    *,
    candidate_id: int,
    label: str,
    reviewer_comment: str | None = None,
    reviewer_name: str | None = None,
    commit: bool = True,
) -> DuplicateTrainingLabelRecord:
    normalized_label = normalize_training_label(
        label
    )

    candidate = db.get(
        DuplicateCandidateRecord,
        candidate_id,
    )

    if candidate is None:
        raise ValueError(
            "Duplicate candidate was not found."
        )

    record = DuplicateTrainingLabelRecord(
        candidate_id=candidate.id,
        label=normalized_label,
        reviewer_comment=(
            reviewer_comment
        ),
        reviewer_name=reviewer_name,
        feature_snapshot=(
            candidate.features
            or {}
        ),
        model_version=(
            candidate.model_version
        ),
    )

    db.add(record)

    if commit:
        db.commit()
        db.refresh(record)
    else:
        db.flush()

    return record


def get_latest_candidate_label(
    db: Session,
    *,
    candidate_id: int,
) -> DuplicateTrainingLabelRecord | None:
    statement = (
        select(
            DuplicateTrainingLabelRecord
        )
        .where(
            DuplicateTrainingLabelRecord
            .candidate_id
            == candidate_id
        )
        .order_by(
            DuplicateTrainingLabelRecord
            .created_at
            .desc(),
            DuplicateTrainingLabelRecord
            .id
            .desc(),
        )
        .limit(1)
    )

    return db.scalars(
        statement
    ).first()


def get_training_rows(
    db: Session,
) -> list[dict[str, Any]]:
    """
    Return only the latest usable reviewer label for
    each candidate.

    UNCERTAIN labels are excluded from model training.
    """

    latest_label_ids = (
        select(
            func.max(
                DuplicateTrainingLabelRecord.id
            ).label("latest_id")
        )
        .group_by(
            DuplicateTrainingLabelRecord
            .candidate_id
        )
        .subquery()
    )

    statement = (
        select(
            DuplicateTrainingLabelRecord
        )
        .join(
            latest_label_ids,
            DuplicateTrainingLabelRecord.id
            == latest_label_ids.c.latest_id,
        )
        .where(
            DuplicateTrainingLabelRecord.label.in_(
                [
                    "DUPLICATE",
                    "NOT_DUPLICATE",
                ]
            )
        )
        .order_by(
            DuplicateTrainingLabelRecord
            .id
            .asc()
        )
    )

    rows = db.scalars(
        statement
    ).all()

    return [
        {
            "id": row.id,
            "candidateId": (
                row.candidate_id
            ),
            "label": row.label,
            "features": (
                row.feature_snapshot
                or {}
            ),
            "modelVersion": (
                row.model_version
            ),
            "reviewerName": (
                row.reviewer_name
            ),
            "reviewerComment": (
                row.reviewer_comment
            ),
            "createdAt": (
                row.created_at.isoformat()
                if row.created_at
                else None
            ),
        }
        for row in rows
    ]


def get_training_label_summary(
    db: Session,
) -> dict[str, Any]:
    rows = get_training_rows(
        db
    )

    duplicate_count = sum(
        1
        for row in rows
        if row["label"]
        == "DUPLICATE"
    )

    not_duplicate_count = sum(
        1
        for row in rows
        if row["label"]
        == "NOT_DUPLICATE"
    )

    total = len(rows)

    return {
        "totalUsableLabels": total,
        "duplicateLabels": (
            duplicate_count
        ),
        "notDuplicateLabels": (
            not_duplicate_count
        ),
        "minimumRequired": 20,
        "readyForTraining": (
            total >= 20
            and duplicate_count > 0
            and not_duplicate_count > 0
        ),
    }