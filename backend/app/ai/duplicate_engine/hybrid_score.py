from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.ai.duplicate_engine.types import ComparisonFeatures


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

    def to_dict(self) -> dict[str, float | None]:
        return {
            "authoritative": round(self.authoritative, 2),
            "identity": round(self.identity, 2),
            "organizational": round(self.organizational, 2),
            "semantic": round(self.semantic, 2),
            "contradictions": round(self.contradictions, 2),
            "missingDataPenalty": round(self.missing_data_penalty, 2),
            "rawScore": round(self.raw_score, 2),
            "finalScore": round(self.final_score, 2),
            "confidenceCap": round(self.confidence_cap, 2) if self.confidence_cap is not None else None,
        }


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(value, maximum))


def _ramp(value: float, *, start: float, end: float, points: float) -> float:
    if value <= start:
        return 0.0
    if value >= end:
        return points
    if end <= start:
        return 0.0
    return (value - start) / (end - start) * points


def _has_name_evidence(features: ComparisonFeatures) -> bool:
    return (
        features.display_name_similarity >= 0.80
        or (features.first_name_similarity >= 0.80 and features.last_name_similarity >= 0.85)
        or features.dynamic_name_matches > 0
    )


def _has_strong_name_evidence(features: ComparisonFeatures) -> bool:
    return (
        features.display_name_similarity >= 0.92
        or (features.first_name_similarity >= 0.90 and features.last_name_similarity >= 0.92)
        or features.dynamic_name_matches >= 2
    )


def _has_authoritative_identifier(features: ComparisonFeatures) -> bool:
    return (
        features.employee_id_exact
        or features.email_exact
        or features.phone_exact
        or features.dynamic_identifier_matches > 0
    )


def _count_independent_evidence(features: ComparisonFeatures) -> int:
    count = 0
    if features.employee_id_exact:
        count += 1
    if features.email_exact or features.email_similarity >= 0.92:
        count += 1
    if features.phone_exact:
        count += 1
    if _has_name_evidence(features):
        count += 1
    if features.username_exact or features.username_similarity >= 0.90:
        count += 1
    if features.manager_exact or features.manager_similarity >= 0.90:
        count += 1
    if features.department_exact:
        count += 1
    count += min(features.dynamic_identifier_matches, 2)
    count += min(features.dynamic_contact_matches, 1)
    count += min(features.dynamic_org_matches, 1)
    return count


def _calculate_authoritative_score(features: ComparisonFeatures) -> float:
    score = 0.0
    if features.employee_id_exact:
        score += 46.0
    if features.email_exact:
        score += 24.0
    if features.phone_exact:
        score += 16.0
    score += min(50.0, features.dynamic_identifier_matches * 40.0)
    score += min(24.0, features.dynamic_contact_matches * 18.0)
    return score


def _calculate_identity_score(features: ComparisonFeatures) -> float:
    score = 0.0
    if features.username_exact:
        score += 10.0
    else:
        score += _ramp(features.username_similarity, start=0.75, end=0.98, points=9.0)

    score += _ramp(features.display_name_similarity, start=0.68, end=0.98, points=14.0)
    score += _ramp(features.first_name_similarity, start=0.72, end=0.98, points=5.0)
    score += _ramp(features.last_name_similarity, start=0.75, end=0.98, points=7.0)

    if not features.email_exact:
        score += _ramp(features.email_similarity, start=0.78, end=0.99, points=8.0)
        score += _ramp(features.email_local_similarity, start=0.78, end=0.98, points=5.0)

    if not features.phone_exact:
        score += _ramp(features.phone_similarity, start=0.86, end=1.00, points=3.0)

    score += min(14.0, features.dynamic_name_matches * 8.0)
    score += min(4.0, features.dynamic_unknown_matches * 2.0)
    return score


def _calculate_organizational_score(features: ComparisonFeatures) -> float:
    score = 0.0
    if features.manager_exact:
        score += 4.0
    else:
        score += _ramp(features.manager_similarity, start=0.82, end=1.00, points=2.5)

    if features.department_exact:
        score += 2.5
    else:
        score += _ramp(features.department_similarity, start=0.85, end=1.00, points=1.0)

    if features.status_exact:
        score += 0.5
    score += _ramp(features.title_similarity, start=0.84, end=1.00, points=2.0)
    score += _ramp(features.location_similarity, start=0.88, end=1.00, points=1.0)
    score += min(6.0, features.dynamic_org_matches * 2.0)
    return score


def _calculate_semantic_score(features: ComparisonFeatures) -> float:
    return (
        _ramp(features.identity_embedding_similarity, start=0.89, end=0.99, points=3.0)
        + _ramp(features.name_embedding_similarity, start=0.91, end=0.99, points=2.0)
        + _ramp(features.organization_embedding_similarity, start=0.93, end=0.99, points=1.0)
    )


def _calculate_contradictions(features: ComparisonFeatures) -> float:
    penalty = 0.0
    if 0 < features.email_similarity < 0.45:
        penalty += 20.0
    elif 0 < features.email_similarity < 0.65:
        penalty += 10.0
    if 0 < features.username_similarity < 0.40:
        penalty += 10.0
    elif 0 < features.username_similarity < 0.60:
        penalty += 5.0
    if 0 < features.first_name_similarity < 0.40:
        penalty += 12.0
    elif 0 < features.first_name_similarity < 0.65:
        penalty += 5.0
    if 0 < features.last_name_similarity < 0.40:
        penalty += 14.0
    elif 0 < features.last_name_similarity < 0.65:
        penalty += 6.0
    if 0 < features.display_name_similarity < 0.40:
        penalty += 16.0
    elif 0 < features.display_name_similarity < 0.65:
        penalty += 7.0
    if 0 < features.department_similarity < 0.35:
        penalty += 3.0
    if 0 < features.manager_similarity < 0.35:
        penalty += 3.0
    penalty += min(45.0, features.dynamic_identifier_conflicts * 25.0)
    return penalty


def _calculate_missing_penalty(features: ComparisonFeatures) -> float:
    return 0.0


def _determine_confidence_cap(features: ComparisonFeatures) -> float | None:
    evidence_count = _count_independent_evidence(features)
    authoritative = _has_authoritative_identifier(features)
    name_evidence = _has_name_evidence(features)
    strong_name = _has_strong_name_evidence(features)
    cap: float | None = None

    def apply_cap(value: float) -> None:
        nonlocal cap
        cap = value if cap is None else min(cap, value)

    if not authoritative and evidence_count == 0:
        apply_cap(24.0)
    if not authoritative and not name_evidence and (
        features.username_exact or features.username_similarity >= 0.75
    ):
        apply_cap(44.0)
    if not authoritative and evidence_count <= 1:
        apply_cap(44.0)
    if not authoritative and evidence_count == 2 and not strong_name:
        apply_cap(52.0)
    if features.dynamic_identifier_conflicts > 0 and not features.employee_id_exact:
        apply_cap(55.0)
    return cap


def _calibrate_raw_score(raw_score: float) -> float:
    positive_raw_score = max(0.0, raw_score)
    return 100.0 * (1.0 - math.exp(-positive_raw_score / 48.0))


def calculate_score_breakdown(features: ComparisonFeatures) -> ScoreBreakdown:
    authoritative = _calculate_authoritative_score(features)
    identity = _calculate_identity_score(features)
    organizational = _calculate_organizational_score(features)
    semantic = _calculate_semantic_score(features)
    contradictions = _calculate_contradictions(features)
    missing_penalty = _calculate_missing_penalty(features)
    raw_score = authoritative + identity + organizational + semantic - contradictions - missing_penalty
    confidence_cap = _determine_confidence_cap(features)
    final_score = _calibrate_raw_score(raw_score)

    if confidence_cap is not None:
        final_score = min(final_score, confidence_cap)

    if (
        features.employee_id_exact
        and features.email_exact
        and _has_strong_name_evidence(features)
        and contradictions < 10.0
    ):
        final_score = max(final_score, 97.0)
    elif (
        features.employee_id_exact
        and (features.email_exact or _has_name_evidence(features))
        and contradictions < 15.0
    ):
        final_score = max(final_score, 91.0)
    elif features.email_exact and _has_strong_name_evidence(features) and contradictions < 15.0:
        final_score = max(final_score, 87.0)
    elif features.phone_exact and _has_strong_name_evidence(features) and contradictions < 15.0:
        final_score = max(final_score, 82.0)
    elif features.dynamic_identifier_matches >= 2 and features.dynamic_identifier_conflicts == 0:
        final_score = max(final_score, 90.0)
    elif (
        features.dynamic_identifier_matches >= 1
        and (features.dynamic_name_matches > 0 or features.dynamic_contact_matches > 0)
        and features.dynamic_identifier_conflicts == 0
    ):
        final_score = max(final_score, 86.0)
    elif (
        features.dynamic_identifier_matches == 1
        and features.dynamic_identifier_conflicts == 0
    ):
        # A source-specific identifier discovered by the application profiler
        # is authoritative enough to enter the review band on its own. A
        # differing username is not treated as a veto because duplicate
        # accounts commonly have different logins by definition. Additional
        # name/contact evidence is still required for high-confidence scores.
        final_score = max(final_score, 52.0)

    final_score = _clamp(min(final_score, 99.5))
    return ScoreBreakdown(
        authoritative=authoritative,
        identity=identity,
        organizational=organizational,
        semantic=semantic,
        contradictions=contradictions,
        missing_data_penalty=missing_penalty,
        raw_score=raw_score,
        final_score=final_score,
        confidence_cap=confidence_cap,
    )


def calculate_hybrid_score(features: ComparisonFeatures) -> float:
    breakdown = calculate_score_breakdown(features)
    logger.debug("Hybrid score breakdown: %s", breakdown.to_dict())
    return round(breakdown.final_score, 2)


def classify_confidence(confidence: float) -> str:
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
