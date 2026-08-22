from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.ai.duplicate_engine.types import DuplicatePrediction
from app.models.account import Account
from app.services.duplicate_detector import (
    detect_application_duplicates,
    get_grouping_edge_reason,
    has_major_contradiction,
    has_name_evidence,
    has_strong_name_evidence,
    prediction_account_key,
)


REVIEW_MINIMUM_CONFIDENCE = 35.0
DYNAMIC_IDENTIFIER_REVIEW_CONFIDENCE = 50.0


def get_review_candidate_reason(
    prediction: DuplicatePrediction,
) -> str | None:
    """Return a conservative review reason for a non-grouped prediction.

    Review eligibility is evidence-aware rather than confidence-only. A pair
    must have multiple independent identity signals (or one profiled identifier)
    and must not contain a major contradiction. Automatic grouping remains
    exclusively controlled by get_grouping_edge_reason().
    """
    if get_grouping_edge_reason(prediction) is not None:
        return None

    if has_major_contradiction(prediction):
        return None

    features = prediction.features
    confidence = float(prediction.confidence)

    # A single dynamically profiled identifier was intentionally calibrated as
    # review-level evidence in Phase 2. It should be visible to a reviewer even
    # when there is not enough support to create a duplicate group.
    if (
        features.dynamic_identifier_matches >= 1
        and features.dynamic_identifier_conflicts == 0
        and confidence >= DYNAMIC_IDENTIFIER_REVIEW_CONFIDENCE
    ):
        return "PROFILED_IDENTIFIER_REVIEW"

    if confidence < REVIEW_MINIMUM_CONFIDENCE:
        return None

    name_match = has_name_evidence(prediction)
    strong_name = has_strong_name_evidence(prediction)

    strong_username = (
        features.username_exact
        or features.username_similarity >= 0.90
    )
    moderate_username = (
        features.username_exact
        or features.username_similarity >= 0.82
    )

    strong_email_local = features.email_local_similarity >= 0.90
    moderate_email_local = features.email_local_similarity >= 0.85

    # Strong first/last or display-name evidence plus a second username signal.
    if strong_name and moderate_username:
        return "STRONG_NAME_WITH_USERNAME_SUPPORT"

    # Three independent fuzzy identity signals. This captures cases where name,
    # username, and email all point toward the same person, but none is exact.
    if name_match and strong_username and strong_email_local:
        return "NAME_USERNAME_EMAIL_REVIEW"

    if strong_name and moderate_email_local:
        return "STRONG_NAME_WITH_EMAIL_SUPPORT"

    if name_match and moderate_username and moderate_email_local:
        return "MULTI_SIGNAL_IDENTITY_REVIEW"

    # Dynamic contact/name evidence can support review but never by itself.
    if (
        features.dynamic_contact_matches >= 1
        and name_match
    ):
        return "PROFILED_CONTACT_WITH_NAME_REVIEW"

    if (
        features.dynamic_name_matches >= 1
        and moderate_username
    ):
        return "PROFILED_NAME_WITH_USERNAME_REVIEW"

    return None


def classify_prediction_decision(
    prediction: DuplicatePrediction,
) -> dict[str, Any]:
    grouping_reason = get_grouping_edge_reason(prediction)
    if grouping_reason is not None:
        return {
            "decision": "GROUP",
            "reason": grouping_reason,
        }

    review_reason = get_review_candidate_reason(prediction)
    if review_reason is not None:
        return {
            "decision": "REVIEW",
            "reason": review_reason,
        }

    if has_major_contradiction(prediction):
        rejection_reason = "MAJOR_CONTRADICTION"
    elif float(prediction.confidence) < REVIEW_MINIMUM_CONFIDENCE:
        rejection_reason = "BELOW_REVIEW_THRESHOLD"
    else:
        rejection_reason = "INSUFFICIENT_INDEPENDENT_EVIDENCE"

    return {
        "decision": "REJECT",
        "reason": rejection_reason,
    }


def prediction_to_review_candidate(
    prediction: DuplicatePrediction,
    *,
    reason: str,
) -> dict[str, Any]:
    features = prediction.features
    return {
        "account1Id": prediction.account_1_id,
        "account2Id": prediction.account_2_id,
        "account1Key": prediction_account_key(prediction.account_1),
        "account2Key": prediction_account_key(prediction.account_2),
        "account1": prediction.account_1.raw,
        "account2": prediction.account_2.raw,
        "confidence": round(float(prediction.confidence), 2),
        "classification": prediction.classification,
        "decision": "REVIEW",
        "reviewReason": reason,
        "modelVersion": prediction.model_version,
        "matchedAttributes": list(features.dynamic_matched_attributes),
        "conflictingAttributes": list(features.dynamic_conflicting_attributes),
        "features": features.to_dict(),
        "reasons": [item.to_dict() for item in prediction.reasons],
        "warnings": [item.to_dict() for item in prediction.warnings],
    }


def detect_review_candidates(
    accounts: list[Account],
) -> list[dict[str, Any]]:
    """Detect evidence-aware review candidates without changing auto groups."""
    by_application: dict[str, list[Account]] = defaultdict(list)
    for account in accounts:
        by_application[str(account.application or "Unknown").strip()].append(account)

    review_candidates: list[dict[str, Any]] = []
    decision_counts: dict[str, int] = defaultdict(int)

    for application, app_accounts in by_application.items():
        predictions = detect_application_duplicates(app_accounts)
        for prediction in predictions:
            outcome = classify_prediction_decision(prediction)
            decision_counts[outcome["decision"]] += 1

            print(
                "[Duplicate Decision] "
                f"Application={application}, "
                f"Pair={prediction_account_key(prediction.account_1)} <-> "
                f"{prediction_account_key(prediction.account_2)}, "
                f"Confidence={round(float(prediction.confidence), 2)}, "
                f"Decision={outcome['decision']}, "
                f"Reason={outcome['reason']}"
            )

            if outcome["decision"] != "REVIEW":
                continue

            review_candidates.append(
                prediction_to_review_candidate(
                    prediction,
                    reason=outcome["reason"],
                )
            )

    review_candidates.sort(
        key=lambda item: (
            -float(item["confidence"]),
            str(item["account1Key"]),
            str(item["account2Key"]),
        )
    )

    print(
        "[Duplicate Detection] DecisionSummary="
        f"{dict(decision_counts)}"
    )

    return review_candidates
