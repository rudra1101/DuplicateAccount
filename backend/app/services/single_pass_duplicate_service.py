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


def _build_application_groups(
    *,
    application: str,
    accounts: list[Account],
    predictions: list[DuplicatePrediction],
    starting_group_id: int,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], int]:
    account_by_key = {
        get_account_identity(account): account
        for account in accounts
    }
    prediction_by_pair: dict[
        tuple[str, str], DuplicatePrediction
    ] = {}
    union_find = UnionFind(list(account_by_key.keys()))
    evidence_counts: dict[str, int] = defaultdict(int)
    grouping_decision_counts: dict[str, int] = defaultdict(int)

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
                and get_grouping_edge_reason(prediction) is not None
            )
        }
        component_accounts = [
            account_by_key[key]
            for key in component_keys
        ]
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
            if prediction is None:
                continue

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
                normalize_key_part(
                    (item.get("account") or {}).get("username")
                ),
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
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[int, dict[str, Any]],
    list[dict[str, Any]],
]:
    """Run candidate generation/scoring once per application.

    The resulting prediction set is reused for automatic grouping and the
    standalone review queue. This removes the Phase 7 second detection pass
    without changing grouping or review thresholds.
    """
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
        )
        if groups:
            all_groups[application] = groups
        all_details.update(details)

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
