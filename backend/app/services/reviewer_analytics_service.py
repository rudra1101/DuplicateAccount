from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.review_candidate import ReviewCandidateRecord
from app.db_models.review_decision_history import ReviewDecisionHistoryRecord


CONFIDENCE_BANDS = [
    (95.0, 100.0, "95-100"),
    (85.0, 95.0, "85-94"),
    (70.0, 85.0, "70-84"),
    (50.0, 70.0, "50-69"),
    (0.0, 50.0, "0-49"),
]

PERCENT_SIMILARITY_RE = re.compile(
    r"^(?P<name>.+?)\s+similarity\s*\((?P<percent>\d+(?:\.\d+)?)%\)$",
    re.IGNORECASE,
)

CORE_ATTRIBUTE_ALIASES = {
    "employee id exact": "Employee ID exact",
    "email exact": "Email exact",
    "phone exact": "Phone exact",
    "username exact": "Username exact",
    "display name exact": "Display name exact",
    "status exact": "Status exact",
}


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def _sample_quality(usable: int) -> str:
    if usable >= 20:
        return "SUFFICIENT"
    if usable >= 8:
        return "DEVELOPING"
    return "LIMITED"


def _confidence_band(value: float | None) -> str:
    if value is None:
        return "Not available"
    for minimum, maximum, label in CONFIDENCE_BANDS:
        if maximum == 100.0:
            if minimum <= value <= maximum:
                return label
        elif minimum <= value < maximum:
            return label
    return "Not available"


def _number(features: dict[str, Any], key: str) -> float:
    try:
        return float(features.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def _truthy(features: dict[str, Any], key: str) -> bool:
    value = features.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _similarity_bucket(percent: float) -> str:
    if percent >= 100.0:
        return "100%"
    if percent >= 95.0:
        return "95-99%"
    if percent >= 90.0:
        return "90-94%"
    if percent >= 85.0:
        return "85-89%"
    return "below 85%"


def _normalize_profiled_attribute(attribute: Any) -> str | None:
    raw = str(attribute or "").strip()
    if not raw:
        return None

    canonical = CORE_ATTRIBUTE_ALIASES.get(raw.lower())
    if canonical is not None:
        return canonical

    match = PERCENT_SIMILARITY_RE.match(raw)
    if match:
        name = " ".join(match.group("name").strip().split())
        percent = float(match.group("percent"))
        return f"Profiled {name.lower()} similarity ({_similarity_bucket(percent)})"

    return f"Profiled attribute: {raw}"


def _evidence_signals(
    features: dict[str, Any] | None,
    matched_attributes: Iterable[Any] | None,
) -> list[str]:
    values = features or {}
    signals: list[str] = []

    if _truthy(values, "employee_id_exact"):
        signals.append("Employee ID exact")
    if _truthy(values, "email_exact"):
        signals.append("Email exact")
    if _truthy(values, "phone_exact"):
        signals.append("Phone exact")
    if _truthy(values, "username_exact"):
        signals.append("Username exact")
    elif _number(values, "username_similarity") >= 0.90:
        signals.append("Strong username similarity")

    display_name = _number(values, "display_name_similarity")
    first_name = _number(values, "first_name_similarity")
    last_name = _number(values, "last_name_similarity")
    if display_name >= 0.92 or (first_name >= 0.90 and last_name >= 0.92):
        signals.append("Strong name similarity")
    elif display_name >= 0.80 or (first_name >= 0.80 and last_name >= 0.85):
        signals.append("Name similarity")

    if _number(values, "email_local_similarity") >= 0.90 and not _truthy(values, "email_exact"):
        signals.append("Strong email-local similarity")

    identifier_matches = int(_number(values, "dynamic_identifier_matches"))
    if identifier_matches >= 2:
        signals.append("Multiple profiled identifiers")
    elif identifier_matches == 1:
        signals.append("Profiled identifier")

    if int(_number(values, "dynamic_contact_matches")) > 0:
        signals.append("Profiled contact")
    if int(_number(values, "dynamic_name_matches")) > 0:
        signals.append("Profiled name")
    if int(_number(values, "dynamic_org_matches")) > 0:
        signals.append("Organizational support")
    if int(_number(values, "dynamic_identifier_conflicts")) > 0:
        signals.append("Identifier conflict")

    for attribute in list(matched_attributes or [])[:6]:
        normalized = _normalize_profiled_attribute(attribute)
        if normalized:
            signals.append(normalized)

    return list(dict.fromkeys(signals))


def _evidence_families(features: dict[str, Any] | None) -> list[str]:
    values = features or {}
    families: list[str] = []

    if _truthy(values, "employee_id_exact") or _number(values, "dynamic_identifier_matches") > 0:
        families.append("Authoritative Identifier")

    if (
        _truthy(values, "email_exact")
        or _truthy(values, "phone_exact")
        or _number(values, "dynamic_contact_matches") > 0
    ):
        families.append("Contact")

    display_name = _number(values, "display_name_similarity")
    first_name = _number(values, "first_name_similarity")
    last_name = _number(values, "last_name_similarity")
    if (
        display_name >= 0.80
        or (first_name >= 0.80 and last_name >= 0.85)
        or _number(values, "dynamic_name_matches") > 0
    ):
        families.append("Name")

    if (
        _truthy(values, "username_exact")
        or _number(values, "username_similarity") >= 0.90
        or _number(values, "email_similarity") >= 0.92
        or _number(values, "email_local_similarity") >= 0.90
    ):
        families.append("Account Handle")

    if (
        _truthy(values, "department_exact")
        or _truthy(values, "manager_exact")
        or _number(values, "manager_similarity") >= 0.90
        or _number(values, "dynamic_org_matches") > 0
    ):
        families.append("Organizational")

    if _number(values, "dynamic_identifier_conflicts") > 0:
        families.append("Contradiction")

    return list(dict.fromkeys(families))


def _append_evidence_result(
    counters: dict[str, dict[str, int]],
    patterns: dict[str, dict[str, int]],
    family_counters: dict[str, dict[str, int]],
    family_patterns: dict[str, dict[str, int]],
    *,
    decision: str,
    features: dict[str, Any] | None,
    matched_attributes: Iterable[Any] | None,
) -> None:
    if decision not in {"DUPLICATE", "NOT_DUPLICATE", "UNCERTAIN"}:
        return

    signals = _evidence_signals(features, matched_attributes)
    if not signals:
        signals = ["No classified evidence"]

    for signal in signals:
        counters[signal][decision] += 1

    patterns[" + ".join(signals[:4])][decision] += 1

    families = _evidence_families(features)
    if not families:
        families = ["Unclassified"]
    for family in families:
        family_counters[family][decision] += 1
    family_patterns[" + ".join(families)][decision] += 1


def _serialize_evidence_rows(
    counters: dict[str, dict[str, int]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for evidence, counts in counters.items():
        duplicates = int(counts.get("DUPLICATE", 0))
        not_duplicates = int(counts.get("NOT_DUPLICATE", 0))
        uncertain = int(counts.get("UNCERTAIN", 0))
        reviewed = duplicates + not_duplicates + uncertain
        usable = duplicates + not_duplicates
        rows.append(
            {
                "evidence": evidence,
                "reviewed": reviewed,
                "usableSamples": usable,
                "confirmedDuplicates": duplicates,
                "notDuplicates": not_duplicates,
                "uncertain": uncertain,
                "confirmationRate": _rate(duplicates, usable),
                "falsePositiveRate": _rate(not_duplicates, usable),
                "sampleQuality": _sample_quality(usable),
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row["reviewed"]),
            -int(row["confirmedDuplicates"]),
            str(row["evidence"]),
        )
    )
    return rows[:limit]


def get_evidence_calibration_analytics(db: Session) -> dict[str, list[dict[str, Any]]]:
    evidence_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pattern_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    family_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    family_pattern_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    group_candidates = db.scalars(
        select(DuplicateCandidateRecord).where(
            DuplicateCandidateRecord.review_decision.is_not(None)
        )
    ).all()
    for record in group_candidates:
        _append_evidence_result(
            evidence_counts,
            pattern_counts,
            family_counts,
            family_pattern_counts,
            decision=str(record.review_decision or "").upper(),
            features=record.features or {},
            matched_attributes=record.matched_attributes or [],
        )

    review_candidates = db.scalars(
        select(ReviewCandidateRecord).where(
            ReviewCandidateRecord.review_decision.is_not(None)
        )
    ).all()
    for record in review_candidates:
        _append_evidence_result(
            evidence_counts,
            pattern_counts,
            family_counts,
            family_pattern_counts,
            decision=str(record.review_decision or "").upper(),
            features=record.features or {},
            matched_attributes=record.matched_attributes or [],
        )

    return {
        "evidencePerformance": _serialize_evidence_rows(evidence_counts, limit=30),
        "evidencePatterns": _serialize_evidence_rows(pattern_counts, limit=20),
        "evidenceFamilyPerformance": _serialize_evidence_rows(family_counts, limit=12),
        "evidenceFamilyPatterns": _serialize_evidence_rows(family_pattern_counts, limit=15),
    }


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
                "sampleQuality": _sample_quality(usable),
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
