from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.ai.duplicate_engine.types import DuplicatePrediction
from app.models.account import Account
from app.services.duplicate_detector import (
    MAX_COMPONENT_SIZE,
    UnionFind,
    build_candidate_entry,
    build_grouping_diagnostic,
    detect_application_duplicates,
    get_account_identity,
    get_grouping_edge_reason,
    normalize_key_part,
    prediction_account_key,
    remove_duplicate_source_records,
    select_primary_account,
)
from app.services.review_candidate_service import (
    classify_prediction_decision,
    prediction_to_review_candidate,
)


FeedbackKey = tuple[str, str, str]


def _pair_feedback_decision(
    pair_feedback: dict[FeedbackKey, str],
    application: str,
    key_1: str,
    key_2: str,
) -> str | None:
    normalized_1, normalized_2 = sorted((key_1, key_2))
    return pair_feedback.get((application, normalized_1, normalized_2))


def _reviewer_confirmed_entry(
    *,
    candidate_number: int,
    account: Account,
    prediction: DuplicatePrediction | None,
) -> dict[str, Any]:
    if prediction is not None:
        entry = build_candidate_entry(
            candidate_number=candidate_number,
            account=account,
            prediction=prediction,
        )
        # Human confirmation changes the durable decision, not the model score.
        # Preserve the current scan's model confidence so reviewer feedback can
        # never manufacture a 100% AI confidence value.
        entry["recommendation"] = "MERGE"
        entry["classification"] = "REVIEWER_CONFIRMED"
        entry["groupingEvidence"] = "REVIEWER_CONFIRMED_DUPLICATE"
        entry["reviewDecision"] = "DUPLICATE"
        return entry

    # A durable reviewer decision may reconstruct a group even when blocking
    # does not generate the pair in the current scan. In that case there is no
    # current model confidence; do not invent one.
    return {
        "id": candidate_number,
        "confidence": 0.0,
        "recommendation": "MERGE",
        "matchedAttributes": [],
        "differentAttributes": [],
        "account": account.model_dump(),
        "classification": "REVIEWER_CONFIRMED",
        "modelVersion": None,
        "groupingEvidence": "REVIEWER_CONFIRMED_DUPLICATE",
        "reasons": [],
        "warnings": [],
        "features": {},
        "reviewDecision": "DUPLICATE",
    }


def _build_application_groups(
    *,
    application: str,
    accounts: list[Account],
    predictions: list[DuplicatePrediction],
    starting_group_id: int,
    pair_feedback: dict[FeedbackKey, str],
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], int]:
    account_by_key = {
        get_account_identity(account): account
        for account in accounts
    }
    prediction_by_pair: dict[tuple[str, str], DuplicatePrediction] = {}
    union_find = UnionFind(list(account_by_key.keys()))
    evidence_counts: dict[str, int] = defaultdict(int)
    grouping_decision_counts: dict[str, int] = defaultdict(int)
    forced_duplicate_pairs: set[tuple[str, str]] = set()
    excluded_pairs: set[tuple[str, str]] = set()

    # Apply durable human decisions even if the current scoring pass does not
    # generate the pair. This is what prevents reviewers from re-confirming the
    # same pair every aggregation.
    account_keys = set(account_by_key)
    for (feedback_app, key_1, key_2), decision in pair_feedback.items():
        if feedback_app != application:
            continue
        if key_1 not in account_keys or key_2 not in account_keys:
            continue
        pair_key = tuple(sorted((key_1, key_2)))
        if decision == "DUPLICATE":
            forced_duplicate_pairs.add(pair_key)
            union_find.union(*pair_key)
            evidence_counts["REVIEWER_CONFIRMED_DUPLICATE"] += 1
            grouping_decision_counts["REVIEWER_CONFIRMED_DUPLICATE"] += 1
            print(
                "[Reviewer Feedback] "
                f"Application={application}, Pair={key_1} <-> {key_2}, "
                "Decision=DUPLICATE, Action=FORCE_GROUP"
            )
        elif decision == "NOT_DUPLICATE":
            excluded_pairs.add(pair_key)
            grouping_decision_counts["REVIEWER_CONFIRMED_NOT_DUPLICATE"] += 1
            print(
                "[Reviewer Feedback] "
                f"Application={application}, Pair={key_1} <-> {key_2}, "
                "Decision=NOT_DUPLICATE, Action=SUPPRESS"
            )

    for prediction in predictions:
        key_1 = prediction_account_key(prediction.account_1)
        key_2 = prediction_account_key(prediction.account_2)
        if (
            key_1 == key_2
            or key_1 not in account_by_key
            or key_2 not in account_by_key
        ):
            continue

        pair_key = tuple(sorted((key_1, key_2)))
        existing = prediction_by_pair.get(pair_key)
        if existing is None or prediction.confidence > existing.confidence:
            prediction_by_pair[pair_key] = prediction

        if pair_key in excluded_pairs:
            continue

        if pair_key in forced_duplicate_pairs:
            continue

        diagnostic = build_grouping_diagnostic(prediction)
        grouping_decision_counts[
            "ACCEPTED"
            if diagnostic["result"] == "ACCEPTED"
            else diagnostic["reason"]
        ] += 1

        print(
            "[Grouping Decision] "
            f"Pair={key_1} <-> {key_2}, "
            f"Confidence={diagnostic['confidence']}, "
            f"Classification={diagnostic['classification']}, "
            f"Result={diagnostic['result']}, "
            f"Reason={diagnostic['reason']}, "
            f"Evidence={diagnostic['evidence']}"
        )

        edge_reason = diagnostic["edgeReason"]
        if edge_reason is None:
            continue

        union_find.union(key_1, key_2)
        evidence_counts[edge_reason] += 1

    print(
        "[Duplicate Detection] "
        f"Application={application}, "
        f"GroupingEdges={sum(evidence_counts.values())}, "
        f"EvidenceCounts={dict(evidence_counts)}"
    )
    print(
        "[Duplicate Detection] "
        f"Application={application}, "
        f"GroupingDecisionSummary={dict(grouping_decision_counts)}"
    )

    components: dict[str, list[str]] = defaultdict(list)
    for account_key in account_by_key:
        components[union_find.find(account_key)].append(account_key)

    groups: list[dict[str, Any]] = []
    details: dict[int, dict[str, Any]] = {}
    group_id = starting_group_id

    for component_keys in components.values():
        if len(component_keys) < 2 or len(component_keys) > MAX_COMPONENT_SIZE:
            continue

        component_key_set = set(component_keys)
        component_predictions = {
            pair_key: prediction
            for pair_key, prediction in prediction_by_pair.items()
            if (
                pair_key[0] in component_key_set
                and pair_key[1] in component_key_set
                and pair_key not in excluded_pairs
                and (
                    pair_key in forced_duplicate_pairs
                    or get_grouping_edge_reason(prediction) is not None
                )
            )
        }
        component_accounts = [account_by_key[key] for key in component_keys]
        primary_account = select_primary_account(
            component_accounts,
            component_predictions,
        )
        primary_key = get_account_identity(primary_account)
        duplicate_entries: list[dict[str, Any]] = []

        for candidate_account in component_accounts:
            candidate_key = get_account_identity(candidate_account)
            if candidate_key == primary_key:
                continue

            pair_key = tuple(sorted((primary_key, candidate_key)))
            prediction = component_predictions.get(pair_key)
            is_forced = pair_key in forced_duplicate_pairs

            if prediction is None and not is_forced:
                continue

            if is_forced:
                duplicate_entries.append(
                    _reviewer_confirmed_entry(
                        candidate_number=len(duplicate_entries) + 1,
                        account=candidate_account,
                        prediction=prediction,
                    )
                )
            elif prediction is not None:
                duplicate_entries.append(
                    build_candidate_entry(
                        candidate_number=len(duplicate_entries) + 1,
                        account=candidate_account,
                        prediction=prediction,
                    )
                )

        if not duplicate_entries:
            continue

        duplicate_entries.sort(
            key=lambda item: (
                -float(item["confidence"]),
                normalize_key_part((item.get("account") or {}).get("username")),
            )
        )
        for index, entry in enumerate(duplicate_entries, start=1):
            entry["id"] = index

        highest_confidence = max(
            float(entry["confidence"])
            for entry in duplicate_entries
        )
        groups.append(
            {
                "groupId": group_id,
                "primaryAccount": primary_account.username,
                "duplicates": len(duplicate_entries),
                "highestConfidence": highest_confidence,
            }
        )
        details[group_id] = {
            "primaryAccount": primary_account.model_dump(),
            "duplicates": duplicate_entries,
        }
        group_id += 1

    groups.sort(
        key=lambda item: (
            -float(item["highestConfidence"]),
            normalize_key_part(item["primaryAccount"]),
        )
    )
    return groups, details, group_id


def analyze_duplicate_decisions(
    accounts: list[Account],
    *,
    pair_feedback: dict[FeedbackKey, str] | None = None,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[int, dict[str, Any]],
    list[dict[str, Any]],
]:
    """Run detection once per app and apply durable reviewer decisions."""
    feedback = pair_feedback or {}
    applications: dict[str, list[Account]] = defaultdict(list)
    for account in accounts:
        application = str(account.application or "Unknown").strip()
        applications[application].append(account)

    all_groups: dict[str, list[dict[str, Any]]] = {}
    all_details: dict[int, dict[str, Any]] = {}
    review_candidates: list[dict[str, Any]] = []
    decision_counts: dict[str, int] = defaultdict(int)
    next_group_id = 1

    for application, raw_accounts in applications.items():
        app_accounts = remove_duplicate_source_records(raw_accounts)
        print(
            "[Duplicate Detection] "
            f"Application={application}, "
            f"InputAccounts={len(raw_accounts)}, "
            f"UniqueSourceAccounts={len(app_accounts)}"
        )

        if len(app_accounts) < 2:
            continue

        predictions = detect_application_duplicates(app_accounts)
        print(
            "[Duplicate Detection] "
            f"Application={application}, "
            f"QualifyingPredictions={len(predictions)}"
        )

        groups, details, next_group_id = _build_application_groups(
            application=application,
            accounts=app_accounts,
            predictions=predictions,
            starting_group_id=next_group_id,
            pair_feedback=feedback,
        )
        if groups:
            all_groups[application] = groups
        all_details.update(details)

        for prediction in predictions:
            key_1 = prediction_account_key(prediction.account_1)
            key_2 = prediction_account_key(prediction.account_2)
            feedback_decision = _pair_feedback_decision(
                feedback,
                application,
                key_1,
                key_2,
            )

            if feedback_decision == "DUPLICATE":
                decision_counts["GROUP"] += 1
                print(
                    "[Duplicate Decision] "
                    f"Application={application}, Pair={key_1} <-> {key_2}, "
                    "Decision=GROUP, Reason=REVIEWER_CONFIRMED_DUPLICATE"
                )
                continue

            if feedback_decision == "NOT_DUPLICATE":
                decision_counts["REJECT"] += 1
                print(
                    "[Duplicate Decision] "
                    f"Application={application}, Pair={key_1} <-> {key_2}, "
                    "Decision=REJECT, Reason=REVIEWER_CONFIRMED_NOT_DUPLICATE"
                )
                continue

            outcome = classify_prediction_decision(prediction)
            decision_counts[outcome["decision"]] += 1
            print(
                "[Duplicate Decision] "
                f"Application={application}, "
                f"Pair={key_1} <-> {key_2}, "
                f"Confidence={round(float(prediction.confidence), 2)}, "
                f"Decision={outcome['decision']}, "
                f"Reason={outcome['reason']}"
            )
            if outcome["decision"] == "REVIEW":
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
    print(
        "[Duplicate Detection] "
        "SinglePassDecisionPipeline=completed"
    )
    return all_groups, all_details, review_candidates
