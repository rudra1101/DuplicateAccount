from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.review_decision_history import ReviewDecisionHistoryRecord


CONFIDENCE_BANDS = [
    (95.0, 100.0, "95-100"),
    (85.0, 95.0, "85-94"),
    (70.0, 85.0, "70-84"),
    (50.0, 70.0, "50-69"),
    (0.0, 50.0, "0-49"),
]


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def _confidence_band(value: float | None) -> str:
    if value is None:
        return "Not available"
    for minimum, maximum, label in CONFIDENCE_BANDS:
        if minimum <= value <= maximum if maximum == 100.0 else minimum <= value < maximum:
            return label
    return "Not available"


def get_reviewer_feedback_analytics(db: Session) -> dict[str, Any]:
    records = list(
        db.scalars(
            select(ReviewDecisionHistoryRecord)
            .order_by(ReviewDecisionHistoryRecord.created_at.desc())
        ).all()
    )

    decision_counts: dict[str, int] = defaultdict(int)
    source_usable: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    band_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    confirmed_confidences: list[float] = []

    for record in records:
        decision = str(record.decision or "").upper()
        decision_counts[decision] += 1

        if decision == "DUPLICATE" and record.confidence is not None:
            confirmed_confidences.append(float(record.confidence))

        if decision in {"DUPLICATE", "NOT_DUPLICATE"}:
            source_usable[str(record.source or "UNKNOWN")][decision] += 1

        band = _confidence_band(
            float(record.confidence) if record.confidence is not None else None
        )
        band_counts[band][decision] += 1

    duplicate_count = decision_counts["DUPLICATE"]
    not_duplicate_count = decision_counts["NOT_DUPLICATE"]
    uncertain_count = decision_counts["UNCERTAIN"]
    usable_count = duplicate_count + not_duplicate_count

    group_counts = source_usable.get("DUPLICATE_GROUP", {})
    group_duplicate = int(group_counts.get("DUPLICATE", 0))
    group_not_duplicate = int(group_counts.get("NOT_DUPLICATE", 0))

    candidate_counts = source_usable.get("REVIEW_CANDIDATE", {})
    candidate_duplicate = int(candidate_counts.get("DUPLICATE", 0))
    candidate_not_duplicate = int(candidate_counts.get("NOT_DUPLICATE", 0))

    ordered_labels = ["95-100", "85-94", "70-84", "50-69", "0-49", "Not available"]
    confidence_bands = []
    for label in ordered_labels:
        counts = band_counts.get(label, {})
        duplicates = int(counts.get("DUPLICATE", 0))
        not_duplicates = int(counts.get("NOT_DUPLICATE", 0))
        uncertain = int(counts.get("UNCERTAIN", 0))
        reviewed = duplicates + not_duplicates + uncertain
        usable = duplicates + not_duplicates
        confidence_bands.append(
            {
                "band": label,
                "reviewed": reviewed,
                "confirmedDuplicates": duplicates,
                "notDuplicates": not_duplicates,
                "uncertain": uncertain,
                "confirmationRate": _rate(duplicates, usable),
            }
        )

    return {
        "reviewedPairs": len(records),
        "confirmedDuplicates": duplicate_count,
        "notDuplicates": not_duplicate_count,
        "uncertain": uncertain_count,
        "usableDecisions": usable_count,
        "reviewAcceptanceRate": _rate(duplicate_count, usable_count),
        "duplicateGroupPrecision": _rate(
            group_duplicate,
            group_duplicate + group_not_duplicate,
        ),
        "reviewCandidateAcceptanceRate": _rate(
            candidate_duplicate,
            candidate_duplicate + candidate_not_duplicate,
        ),
        "averageConfirmedConfidence": (
            round(sum(confirmed_confidences) / len(confirmed_confidences), 2)
            if confirmed_confidences
            else None
        ),
        "confidenceBands": confidence_bands,
    }
