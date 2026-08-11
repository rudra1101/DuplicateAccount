from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.ai.duplicate_engine.types import (
    ComparisonFeatures,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreBreakdown:
    authoritative: float
    identity: float
    organizational: float
    semantic: float
    contradictions: float
    missing_data_penalty: float
    raw_score: float
    final_score: float
    confidence_cap: float | None

    def to_dict(
        self,
    ) -> dict[str, float | None]:
        return {
            "authoritative": round(
                self.authoritative,
                2,
            ),
            "identity": round(
                self.identity,
                2,
            ),
            "organizational": round(
                self.organizational,
                2,
            ),
            "semantic": round(
                self.semantic,
                2,
            ),
            "contradictions": round(
                self.contradictions,
                2,
            ),
            "missingDataPenalty": round(
                self.missing_data_penalty,
                2,
            ),
            "rawScore": round(
                self.raw_score,
                2,
            ),
            "finalScore": round(
                self.final_score,
                2,
            ),
            "confidenceCap": (
                round(
                    self.confidence_cap,
                    2,
                )
                if self.confidence_cap
                is not None
                else None
            ),
        }


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


def _ramp(
    value: float,
    *,
    start: float,
    end: float,
    points: float,
) -> float:
    """
    Convert a similarity value into continuous evidence points.

    value <= start -> 0 points
    value >= end   -> full points
    """

    if value <= start:
        return 0.0

    if value >= end:
        return points

    if end <= start:
        return 0.0

    return (
        (value - start)
        / (end - start)
        * points
    )


def _missing_ratio(
    features: ComparisonFeatures,
) -> float:
    total_fields = 22

    missing_fields = (
        features.account_1_missing_fields
        + features.account_2_missing_fields
    )

    return min(
        1.0,
        missing_fields
        / total_fields,
    )


def _has_name_evidence(
    features: ComparisonFeatures,
) -> bool:
    return (
        features.display_name_similarity
        >= 0.80
        or (
            features.first_name_similarity
            >= 0.80
            and features.last_name_similarity
            >= 0.85
        )
    )


def _has_strong_name_evidence(
    features: ComparisonFeatures,
) -> bool:
    return (
        features.display_name_similarity
        >= 0.92
        or (
            features.first_name_similarity
            >= 0.90
            and features.last_name_similarity
            >= 0.92
        )
    )


def _has_authoritative_identifier(
    features: ComparisonFeatures,
) -> bool:
    return (
        features.employee_id_exact
        or features.email_exact
        or features.phone_exact
    )


def _count_independent_evidence(
    features: ComparisonFeatures,
) -> int:
    """
    Count independent evidence categories.

    Related attributes such as email similarity and email-local
    similarity are counted as one evidence category.
    """

    count = 0

    if features.employee_id_exact:
        count += 1

    if (
        features.email_exact
        or features.email_similarity
        >= 0.92
    ):
        count += 1

    if features.phone_exact:
        count += 1

    if _has_name_evidence(
        features
    ):
        count += 1

    if (
        features.username_exact
        or features.username_similarity
        >= 0.90
    ):
        count += 1

    if (
        features.manager_exact
        or features.manager_similarity
        >= 0.90
    ):
        count += 1

    if features.department_exact:
        count += 1

    return count


def _calculate_authoritative_score(
    features: ComparisonFeatures,
) -> float:
    score = 0.0

    if features.employee_id_exact:
        score += 46.0

    if features.email_exact:
        score += 24.0

    if features.phone_exact:
        score += 16.0

    return score


def _calculate_identity_score(
    features: ComparisonFeatures,
) -> float:
    score = 0.0

    if features.username_exact:
        score += 10.0

    else:
        score += _ramp(
            features.username_similarity,
            start=0.78,
            end=0.98,
            points=8.0,
        )

    score += _ramp(
        features.display_name_similarity,
        start=0.72,
        end=0.98,
        points=13.0,
    )

    score += _ramp(
        features.first_name_similarity,
        start=0.75,
        end=0.98,
        points=5.0,
    )

    score += _ramp(
        features.last_name_similarity,
        start=0.78,
        end=0.98,
        points=7.0,
    )

    if not features.email_exact:
        score += _ramp(
            features.email_similarity,
            start=0.82,
            end=0.99,
            points=7.0,
        )

        score += _ramp(
            features.email_local_similarity,
            start=0.82,
            end=0.98,
            points=4.0,
        )

    score += _ramp(
        features.phone_similarity,
        start=0.88,
        end=1.00,
        points=3.0,
    )

    return score


def _calculate_organizational_score(
    features: ComparisonFeatures,
) -> float:
    score = 0.0

    if features.manager_exact:
        score += 4.0

    else:
        score += _ramp(
            features.manager_similarity,
            start=0.85,
            end=1.00,
            points=2.5,
        )

    if features.department_exact:
        score += 2.5

    else:
        score += _ramp(
            features.department_similarity,
            start=0.88,
            end=1.00,
            points=1.0,
        )

    if features.status_exact:
        score += 0.5

    score += _ramp(
        features.title_similarity,
        start=0.86,
        end=1.00,
        points=2.0,
    )

    score += _ramp(
        features.location_similarity,
        start=0.90,
        end=1.00,
        points=1.0,
    )

    return score


def _calculate_semantic_score(
    features: ComparisonFeatures,
) -> float:
    score = 0.0

    score += _ramp(
        features.identity_embedding_similarity,
        start=0.90,
        end=0.99,
        points=3.0,
    )

    score += _ramp(
        features.name_embedding_similarity,
        start=0.92,
        end=0.99,
        points=2.0,
    )

    score += _ramp(
        features.organization_embedding_similarity,
        start=0.94,
        end=0.99,
        points=1.0,
    )

    return score


def _calculate_contradictions(
    features: ComparisonFeatures,
) -> float:
    """
    Return a positive penalty amount.

    This value is subtracted from the positive evidence score.
    """

    penalty = 0.0

    if (
        features.email_similarity > 0
        and features.email_similarity
        < 0.45
    ):
        penalty += 20.0

    elif (
        features.email_similarity > 0
        and features.email_similarity
        < 0.65
    ):
        penalty += 10.0

    if (
        features.username_similarity > 0
        and features.username_similarity
        < 0.40
    ):
        penalty += 10.0

    elif (
        features.username_similarity > 0
        and features.username_similarity
        < 0.60
    ):
        penalty += 5.0

    if (
        features.first_name_similarity > 0
        and features.first_name_similarity
        < 0.40
    ):
        penalty += 12.0

    elif (
        features.first_name_similarity > 0
        and features.first_name_similarity
        < 0.65
    ):
        penalty += 5.0

    if (
        features.last_name_similarity > 0
        and features.last_name_similarity
        < 0.40
    ):
        penalty += 14.0

    elif (
        features.last_name_similarity > 0
        and features.last_name_similarity
        < 0.65
    ):
        penalty += 6.0

    if (
        features.display_name_similarity > 0
        and features.display_name_similarity
        < 0.40
    ):
        penalty += 16.0

    elif (
        features.display_name_similarity > 0
        and features.display_name_similarity
        < 0.65
    ):
        penalty += 7.0

    if (
        features.department_similarity > 0
        and features.department_similarity
        < 0.35
    ):
        penalty += 3.0

    if (
        features.manager_similarity > 0
        and features.manager_similarity
        < 0.35
    ):
        penalty += 3.0

    if (
        features.same_application
        and not _has_authoritative_identifier(
            features
        )
    ):
        penalty += 10.0

    return penalty


def _calculate_missing_penalty(
    features: ComparisonFeatures,
) -> float:
    missing_ratio = _missing_ratio(
        features
    )

    if missing_ratio < 0.20:
        return missing_ratio * 4.0

    if missing_ratio < 0.40:
        return missing_ratio * 7.0

    if missing_ratio < 0.60:
        return missing_ratio * 10.0

    return missing_ratio * 13.0


def _determine_confidence_cap(
    features: ComparisonFeatures,
) -> float | None:
    """
    Prevent weak evidence combinations from becoming
    review-quality matches.
    """

    missing_ratio = _missing_ratio(
        features
    )

    evidence_count = (
        _count_independent_evidence(
            features
        )
    )

    authoritative = (
        _has_authoritative_identifier(
            features
        )
    )

    name_evidence = (
        _has_name_evidence(
            features
        )
    )

    strong_name = (
        _has_strong_name_evidence(
            features
        )
    )

    cap: float | None = None

    def apply_cap(
        value: float,
    ) -> None:
        nonlocal cap

        cap = (
            value
            if cap is None
            else min(
                cap,
                value,
            )
        )

    if (
        not authoritative
        and evidence_count == 0
    ):
        apply_cap(
            24.0
        )

    if (
        not authoritative
        and not name_evidence
        and (
            features.username_exact
            or features.username_similarity
            >= 0.75
        )
    ):
        apply_cap(
            42.0
        )

    if (
        not authoritative
        and evidence_count <= 1
    ):
        apply_cap(
            42.0
        )

    if (
        not authoritative
        and evidence_count == 2
        and not strong_name
    ):
        apply_cap(
            48.0
        )

    if (
        features.same_application
        and not authoritative
        and evidence_count < 3
    ):
        apply_cap(
            46.0
        )

    if (
        missing_ratio >= 0.60
        and not authoritative
    ):
        if evidence_count < 3:
            apply_cap(
                40.0
            )

        else:
            apply_cap(
                55.0
            )

    if (
        missing_ratio >= 0.75
        and not features.employee_id_exact
        and not features.email_exact
    ):
        apply_cap(
            45.0
        )

    return cap


def _calibrate_raw_score(
    raw_score: float,
) -> float:
    """
    Convert additive evidence into a saturating confidence score.

    This preserves ordering while preventing many strong matches
    from collapsing to exactly 100.

    Approximate behavior:

    raw 30  -> 46%
    raw 50  -> 65%
    raw 70  -> 78%
    raw 90  -> 87%
    raw 110 -> 92%
    raw 140 -> 97%
    """

    positive_raw_score = max(
        0.0,
        raw_score,
    )

    return (
        100.0
        * (
            1.0
            - math.exp(
                -positive_raw_score
                / 48.0
            )
        )
    )


def calculate_score_breakdown(
    features: ComparisonFeatures,
) -> ScoreBreakdown:
    authoritative = (
        _calculate_authoritative_score(
            features
        )
    )

    identity = (
        _calculate_identity_score(
            features
        )
    )

    organizational = (
        _calculate_organizational_score(
            features
        )
    )

    semantic = (
        _calculate_semantic_score(
            features
        )
    )

    contradictions = (
        _calculate_contradictions(
            features
        )
    )

    missing_penalty = (
        _calculate_missing_penalty(
            features
        )
    )

    raw_score = (
        authoritative
        + identity
        + organizational
        + semantic
        - contradictions
        - missing_penalty
    )

    confidence_cap = (
        _determine_confidence_cap(
            features
        )
    )

    final_score = (
        _calibrate_raw_score(
            raw_score
        )
    )

    if confidence_cap is not None:
        final_score = min(
            final_score,
            confidence_cap,
        )

    # -------------------------------------------------
    # Strong deterministic combinations
    # -------------------------------------------------

    if (
        features.employee_id_exact
        and features.email_exact
        and _has_strong_name_evidence(
            features
        )
        and contradictions < 10.0
    ):
        final_score = max(
            final_score,
            97.0,
        )

    elif (
        features.employee_id_exact
        and (
            features.email_exact
            or _has_name_evidence(
                features
            )
        )
        and contradictions < 15.0
    ):
        final_score = max(
            final_score,
            91.0,
        )

    elif (
        features.email_exact
        and _has_strong_name_evidence(
            features
        )
        and contradictions < 15.0
    ):
        final_score = max(
            final_score,
            87.0,
        )

    elif (
        features.phone_exact
        and _has_strong_name_evidence(
            features
        )
        and contradictions < 15.0
    ):
        final_score = max(
            final_score,
            82.0,
        )

    # Exactly 100 should be reserved for raw-record equality.
    # ComparisonFeatures does not currently expose complete raw
    # equality, so the model is capped at 99.5.
    final_score = min(
        final_score,
        99.5,
    )

    final_score = _clamp(
        final_score
    )

    return ScoreBreakdown(
        authoritative=authoritative,
        identity=identity,
        organizational=organizational,
        semantic=semantic,
        contradictions=contradictions,
        missing_data_penalty=(
            missing_penalty
        ),
        raw_score=raw_score,
        final_score=final_score,
        confidence_cap=(
            confidence_cap
        ),
    )


def calculate_hybrid_score(
    features: ComparisonFeatures,
) -> float:
    """
    Calculate calibrated duplicate confidence.

    Authoritative identifiers remain dominant, but the final
    confidence uses a saturating calibration curve rather than
    directly clamping an additive evidence total.
    """

    breakdown = (
        calculate_score_breakdown(
            features
        )
    )

    logger.debug(
        "Hybrid score breakdown: %s",
        breakdown.to_dict(),
    )

    return round(
        breakdown.final_score,
        2,
    )


def classify_confidence(
    confidence: float,
) -> str:
    if confidence >= 95:
        return "VERY_HIGH"

    if confidence >= 85:
        return "HIGH"

    if confidence >= 70:
        return "REVIEW_REQUIRED"

    if confidence >= 50:
        return "POSSIBLE_MATCH"

    if confidence >= 30:
        return "WEAK_MATCH"

    return "UNLIKELY"