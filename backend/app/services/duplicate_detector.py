from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.ai.duplicate_engine import (
    duplicate_detection_engine,
)
from app.ai.duplicate_engine.evidence_attributes import (
    build_different_attributes,
    build_matched_attributes,
)
from app.ai.duplicate_engine.types import (
    DuplicatePrediction,
)
from app.models.account import Account


GROUP_MINIMUM_CONFIDENCE = 20.0
GROUP_LINK_CONFIDENCE = 45.0
NON_AUTHORITATIVE_LINK_CONFIDENCE = 58.0

MAX_BLOCK_SIZE = 100
MAX_CANDIDATES_PER_ACCOUNT = 15
MINIMUM_BLOCKING_SCORE = 4.0
MAX_COMPONENT_SIZE = 25


def account_to_dict(
    account: Account,
) -> dict[str, Any]:
    return account.model_dump()


def normalize_key_part(
    value: Any,
) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
    )


def get_account_identity(
    account: Account,
) -> str:
    application = normalize_key_part(
        account.application
        or "Unknown"
    )

    account_id = normalize_key_part(
        account.id
    )

    if account_id:
        return (
            f"{application}:{account_id}"
        )

    username = normalize_key_part(
        account.username
    )

    return (
        f"{application}:username:{username}"
    )


def prediction_account_key(
    prediction_account: Any,
) -> str:
    application = normalize_key_part(
        prediction_account.application
        or "Unknown"
    )

    account_id = normalize_key_part(
        prediction_account.original_id()
    )

    if account_id:
        return (
            f"{application}:{account_id}"
        )

    username = normalize_key_part(
        prediction_account.username
    )

    return (
        f"{application}:username:{username}"
    )


def is_same_source_account(
    account_1: Account,
    account_2: Account,
) -> bool:
    return (
        get_account_identity(account_1)
        == get_account_identity(account_2)
    )


def account_completeness(
    account: Account,
) -> int:
    values = (
        account.id,
        account.username,
        account.displayName,
        account.email,
        account.employeeId,
        account.department,
        account.manager,
        account.status,
        account.created,
    )

    return sum(
        1
        for value in values
        if value is not None
        and str(value).strip()
    )


def remove_duplicate_source_records(
    accounts: list[Account],
) -> list[Account]:
    unique_accounts: dict[
        str,
        Account,
    ] = {}

    for account in accounts:
        identity = get_account_identity(
            account
        )

        existing = unique_accounts.get(
            identity
        )

        if (
            existing is None
            or account_completeness(account)
            > account_completeness(existing)
        ):
            unique_accounts[
                identity
            ] = account

        if existing is not None:
            print(
                "[Duplicate Detection] "
                "Skipped repeated source record: "
                f"{identity}"
            )

    return list(
        unique_accounts.values()
    )


def calculate_confidence(
    account1: Account,
    account2: Account,
) -> tuple[
    float,
    list[str],
    list[str],
]:
    if is_same_source_account(
        account1,
        account2,
    ):
        raise ValueError(
            "Cannot calculate duplicate "
            "confidence for the same "
            "source account."
        )

    prediction = (
        duplicate_detection_engine.compare(
            account_to_dict(account1),
            account_to_dict(account2),
            include_embeddings=True,
        )
    )

    return (
        prediction.confidence,
        build_matched_attributes(
            prediction
        ),
        build_different_attributes(
            prediction
        ),
    )


def has_name_evidence(
    prediction: DuplicatePrediction,
) -> bool:
    features = prediction.features

    return (
        features.display_name_similarity
        >= 0.80
        or (
            features.first_name_similarity
            >= 0.80
            and features.last_name_similarity
            >= 0.85
        )
        or features.dynamic_name_matches > 0
    )


def has_strong_name_evidence(
    prediction: DuplicatePrediction,
) -> bool:
    features = prediction.features

    return (
        features.display_name_similarity
        >= 0.92
        or (
            features.first_name_similarity
            >= 0.90
            and features.last_name_similarity
            >= 0.92
        )
        or features.dynamic_name_matches >= 2
    )


def has_major_contradiction(
    prediction: DuplicatePrediction,
) -> bool:
    features = prediction.features

    return any(
        (
            features.dynamic_identifier_conflicts > 0,
            (
                features.email_similarity > 0
                and features.email_similarity
                < 0.45
            ),
            (
                features.display_name_similarity
                > 0
                and features.display_name_similarity
                < 0.45
            ),
            (
                features.first_name_similarity
                > 0
                and features.first_name_similarity
                < 0.40
            ),
            (
                features.last_name_similarity
                > 0
                and features.last_name_similarity
                < 0.40
            ),
        )
    )


def get_grouping_edge_reason(
    prediction: DuplicatePrediction,
) -> str | None:
    confidence = float(
        prediction.confidence
    )

    features = prediction.features

    if confidence < GROUP_LINK_CONFIDENCE:
        return None

    if has_major_contradiction(
        prediction
    ):
        return None

    name_match = has_name_evidence(
        prediction
    )

    strong_name = (
        has_strong_name_evidence(
            prediction
        )
    )

    strong_username = (
        features.username_exact
        or features.username_similarity
        >= 0.90
    )

    strong_email_local = (
        features.email_local_similarity
        >= 0.90
    )

    organizational_support = (
        features.department_exact
        or features.manager_exact
        or features.dynamic_org_matches > 0
    )

    dynamic_identity_support = (
        name_match
        or strong_username
        or strong_email_local
        or features.dynamic_contact_matches > 0
    )

    if (
        features.dynamic_identifier_matches >= 2
        and confidence >= 70.0
    ):
        return "MULTIPLE_DYNAMIC_IDENTIFIERS"

    if (
        features.dynamic_identifier_matches >= 1
        and dynamic_identity_support
        and confidence >= 60.0
    ):
        return "DYNAMIC_IDENTIFIER_WITH_IDENTITY_SUPPORT"

    if (
        features.dynamic_contact_matches >= 1
        and name_match
        and confidence >= 65.0
    ):
        return "DYNAMIC_CONTACT_WITH_NAME_SUPPORT"

    if (
        features.dynamic_name_matches >= 1
        and strong_username
        and confidence >= 60.0
    ):
        return "DYNAMIC_NAME_WITH_USERNAME_SUPPORT"

    if (
        features.employee_id_exact
        and (
            features.email_exact
            or name_match
            or strong_username
        )
    ):
        return (
            "EMPLOYEE_ID_WITH_IDENTITY_SUPPORT"
        )

    if (
        features.email_exact
        and (
            name_match
            or features.username_similarity
            >= 0.80
        )
    ):
        return (
            "EXACT_EMAIL_WITH_IDENTITY_SUPPORT"
        )

    if (
        features.phone_exact
        and (
            strong_name
            or strong_username
        )
    ):
        return (
            "EXACT_PHONE_WITH_IDENTITY_SUPPORT"
        )

    if (
        features.username_exact
        and strong_email_local
    ):
        return (
            "EXACT_USERNAME_AND_EMAIL_LOCAL"
        )

    if (
        strong_username
        and strong_email_local
        and confidence >= 50.0
    ):
        return (
            "STRONG_USERNAME_AND_EMAIL_LOCAL"
        )

    if (
        features.username_exact
        and organizational_support
        and confidence >= 50.0
    ):
        return (
            "EXACT_USERNAME_AND_ORG_CONTEXT"
        )

    if (
        confidence
        < NON_AUTHORITATIVE_LINK_CONFIDENCE
    ):
        return None

    if (
        strong_name
        and strong_username
    ):
        return (
            "STRONG_NAME_AND_USERNAME"
        )

    if (
        strong_name
        and strong_email_local
    ):
        return (
            "STRONG_NAME_AND_EMAIL_LOCAL"
        )

    return None


def get_grouping_rejection_reason(
    prediction: DuplicatePrediction,
) -> str:
    confidence = float(prediction.confidence)
    features = prediction.features

    if confidence < GROUP_LINK_CONFIDENCE:
        return "BELOW_GROUP_LINK_CONFIDENCE"

    if has_major_contradiction(prediction):
        return "MAJOR_CONTRADICTION"

    name_match = has_name_evidence(prediction)
    strong_username = (
        features.username_exact
        or features.username_similarity >= 0.90
    )
    strong_email_local = (
        features.email_local_similarity >= 0.90
    )
    dynamic_identity_support = (
        name_match
        or strong_username
        or strong_email_local
        or features.dynamic_contact_matches > 0
    )

    if (
        features.dynamic_identifier_matches >= 1
        and dynamic_identity_support
        and confidence < 60.0
    ):
        return "DYNAMIC_IDENTIFIER_BELOW_GROUP_THRESHOLD"

    if confidence < NON_AUTHORITATIVE_LINK_CONFIDENCE:
        return "BELOW_NON_AUTHORITATIVE_THRESHOLD"

    return "INSUFFICIENT_INDEPENDENT_EVIDENCE"


def build_grouping_diagnostic(
    prediction: DuplicatePrediction,
) -> dict[str, Any]:
    features = prediction.features
    edge_reason = get_grouping_edge_reason(prediction)
    accepted = edge_reason is not None

    return {
        "result": "ACCEPTED" if accepted else "REJECTED",
        "reason": (
            edge_reason
            if accepted
            else get_grouping_rejection_reason(prediction)
        ),
        "edgeReason": edge_reason,
        "confidence": round(float(prediction.confidence), 2),
        "classification": prediction.classification,
        "evidence": {
            "employeeIdExact": features.employee_id_exact,
            "emailExact": features.email_exact,
            "phoneExact": features.phone_exact,
            "usernameExact": features.username_exact,
            "usernameSimilarity": round(float(features.username_similarity), 4),
            "emailSimilarity": round(float(features.email_similarity), 4),
            "emailLocalSimilarity": round(float(features.email_local_similarity), 4),
            "displayNameSimilarity": round(float(features.display_name_similarity), 4),
            "firstNameSimilarity": round(float(features.first_name_similarity), 4),
            "lastNameSimilarity": round(float(features.last_name_similarity), 4),
            "departmentExact": features.department_exact,
            "managerExact": features.manager_exact,
            "dynamicIdentifierMatches": features.dynamic_identifier_matches,
            "dynamicIdentifierConflicts": features.dynamic_identifier_conflicts,
            "dynamicContactMatches": features.dynamic_contact_matches,
            "dynamicNameMatches": features.dynamic_name_matches,
            "dynamicOrgMatches": features.dynamic_org_matches,
            "dynamicMatchedAttributes": list(features.dynamic_matched_attributes),
            "dynamicConflictingAttributes": list(features.dynamic_conflicting_attributes),
        },
    }


def is_valid_grouping_edge(
    prediction: DuplicatePrediction,
) -> bool:
    return (
        get_grouping_edge_reason(
            prediction
        )
        is not None
    )


class UnionFind:
    def __init__(
        self,
        account_keys: list[str],
    ) -> None:
        self.parent = {
            key: key
            for key in account_keys
        }

        self.rank = {
            key: 0
            for key in account_keys
        }

    def find(
        self,
        key: str,
    ) -> str:
        parent = self.parent[
            key
        ]

        if parent != key:
            self.parent[key] = (
                self.find(parent)
            )

        return self.parent[
            key
        ]

    def union(
        self,
        key_1: str,
        key_2: str,
    ) -> None:
        root_1 = self.find(
            key_1
        )

        root_2 = self.find(
            key_2
        )

        if root_1 == root_2:
            return

        rank_1 = self.rank[
            root_1
        ]

        rank_2 = self.rank[
            root_2
        ]

        if rank_1 < rank_2:
            self.parent[
                root_1
            ] = root_2
            return

        if rank_1 > rank_2:
            self.parent[
                root_2
            ] = root_1
            return

        self.parent[
            root_2
        ] = root_1

        self.rank[
            root_1
        ] += 1


def select_primary_account(
    accounts: list[Account],
    predictions: dict[
        tuple[str, str],
        DuplicatePrediction,
    ],
) -> Account:
    def score(
        account: Account,
    ) -> tuple[
        int,
        float,
        int,
        str,
    ]:
        key = get_account_identity(
            account
        )

        direct_predictions = [
            prediction
            for pair, prediction
            in predictions.items()
            if key in pair
        ]

        return (
            len(
                direct_predictions
            ),
            sum(
                float(
                    prediction.confidence
                )
                for prediction
                in direct_predictions
            ),
            account_completeness(
                account
            ),
            normalize_key_part(
                account.username
            ),
        )

    return max(
        accounts,
        key=score,
    )


def detect_application_duplicates(
    accounts: list[Account],
) -> list[DuplicatePrediction]:
    if len(accounts) < 2:
        return []

    predictions = (
        duplicate_detection_engine.detect(
            [
                account_to_dict(account)
                for account in accounts
            ],
            minimum_confidence=(
                GROUP_MINIMUM_CONFIDENCE
            ),
            cross_application_only=False,
            include_embeddings=True,
            max_block_size=(
                MAX_BLOCK_SIZE
            ),
            max_candidates_per_account=(
                MAX_CANDIDATES_PER_ACCOUNT
            ),
            minimum_blocking_score=(
                MINIMUM_BLOCKING_SCORE
            ),
        )
    )

    valid_predictions: list[
        DuplicatePrediction
    ] = []

    seen_pairs: set[
        tuple[str, str]
    ] = set()

    for prediction in predictions:
        key_1 = (
            prediction_account_key(
                prediction.account_1
            )
        )

        key_2 = (
            prediction_account_key(
                prediction.account_2
            )
        )

        if key_1 == key_2:
            continue

        pair_key = tuple(
            sorted(
                (
                    key_1,
                    key_2,
                )
            )
        )

        if pair_key in seen_pairs:
            continue

        seen_pairs.add(
            pair_key
        )

        valid_predictions.append(
            prediction
        )

    return valid_predictions


def build_recommendation(
    confidence: float,
) -> str:
    if confidence >= 95:
        return "MERGE"

    if confidence >= 50:
        return "REVIEW"

    return "LOW_PRIORITY"


def build_candidate_entry(
    *,
    candidate_number: int,
    account: Account,
    prediction: DuplicatePrediction,
) -> dict[str, Any]:
    confidence = float(
        prediction.confidence
    )

    return {
        "id": candidate_number,
        "confidence": confidence,
        "recommendation": (
            build_recommendation(
                confidence
            )
        ),
        "matchedAttributes": (
            build_matched_attributes(
                prediction
            )
        ),
        "differentAttributes": (
            build_different_attributes(
                prediction
            )
        ),
        "account": (
            account.model_dump()
        ),
        "classification": (
            prediction.classification
        ),
        "modelVersion": (
            prediction.model_version
        ),
        "groupingEvidence": (
            get_grouping_edge_reason(
                prediction
            )
        ),
        "reasons": [
            reason.to_dict()
            for reason
            in prediction.reasons
        ],
        "warnings": [
            warning.to_dict()
            for warning
            in prediction.warnings
        ],
        "features": (
            prediction.features.to_dict()
        ),
    }


def detect_duplicate_groups(
    accounts: list[Account],
) -> tuple[
    dict[
        str,
        list[dict[str, Any]],
    ],
    dict[
        int,
        dict[str, Any],
    ],
]:
    applications: dict[
        str,
        list[Account],
    ] = defaultdict(list)

    for account in accounts:
        application = str(
            account.application
            or "Unknown"
        ).strip()

        applications[
            application
        ].append(
            account
        )

    results: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    details: dict[
        int,
        dict[str, Any],
    ] = {}

    group_id = 1

    for (
        application,
        raw_accounts,
    ) in applications.items():
        app_accounts = (
            remove_duplicate_source_records(
                raw_accounts
            )
        )

        print(
            "[Duplicate Detection] "
            f"Application={application}, "
            f"InputAccounts="
            f"{len(raw_accounts)}, "
            f"UniqueSourceAccounts="
            f"{len(app_accounts)}"
        )

        if len(app_accounts) < 2:
            continue

        account_by_key = {
            get_account_identity(
                account
            ): account
            for account in app_accounts
        }

        predictions = (
            detect_application_duplicates(
                app_accounts
            )
        )

        print(
            "[Duplicate Detection] "
            f"Application={application}, "
            f"QualifyingPredictions="
            f"{len(predictions)}"
        )

        if not predictions:
            continue

        prediction_by_pair: dict[
            tuple[str, str],
            DuplicatePrediction,
        ] = {}

        union_find = UnionFind(
            list(
                account_by_key.keys()
            )
        )

        evidence_counts: dict[
            str,
            int,
        ] = defaultdict(int)

        decision_counts: dict[
            str,
            int,
        ] = defaultdict(int)

        for prediction in predictions:
            key_1 = (
                prediction_account_key(
                    prediction.account_1
                )
            )

            key_2 = (
                prediction_account_key(
                    prediction.account_2
                )
            )

            if (
                key_1 == key_2
                or key_1
                not in account_by_key
                or key_2
                not in account_by_key
            ):
                continue

            pair_key = tuple(
                sorted(
                    (
                        key_1,
                        key_2,
                    )
                )
            )

            existing = (
                prediction_by_pair.get(
                    pair_key
                )
            )

            if (
                existing is None
                or prediction.confidence
                > existing.confidence
            ):
                prediction_by_pair[
                    pair_key
                ] = prediction

            diagnostic = build_grouping_diagnostic(
                prediction
            )

            username_1 = str(
                prediction.account_1.username
                or prediction.account_1.original_id()
                or key_1
            )
            username_2 = str(
                prediction.account_2.username
                or prediction.account_2.original_id()
                or key_2
            )

            print(
                "[Grouping Decision] "
                f"Pair={username_1} <-> {username_2}, "
                f"Confidence={diagnostic['confidence']}, "
                f"Classification={diagnostic['classification']}, "
                f"Result={diagnostic['result']}, "
                f"Reason={diagnostic['reason']}, "
                f"Evidence={diagnostic['evidence']}"
            )

            if diagnostic[
                "result"
            ] == "ACCEPTED":
                decision_counts[
                    "ACCEPTED"
                ] += 1
            else:
                decision_counts[
                    str(diagnostic["reason"])
                ] += 1

            edge_reason = diagnostic[
                "edgeReason"
            ]

            if edge_reason is None:
                continue

            union_find.union(
                key_1,
                key_2,
            )

            evidence_counts[
                str(edge_reason)
            ] += 1

        print(
            "[Duplicate Detection] "
            f"Application={application}, "
            f"GroupingEdges="
            f"{sum(evidence_counts.values())}, "
            f"EvidenceCounts="
            f"{dict(evidence_counts)}"
        )

        print(
            "[Duplicate Detection] "
            f"Application={application}, "
            "GroupingDecisionSummary="
            f"{dict(decision_counts)}"
        )

        components: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for account_key in (
            account_by_key
        ):
            components[
                union_find.find(
                    account_key
                )
            ].append(
                account_key
            )

        for component_keys in (
            components.values()
        ):
            if (
                len(component_keys) < 2
                or len(component_keys)
                > MAX_COMPONENT_SIZE
            ):
                continue

            component_key_set = set(
                component_keys
            )

            component_predictions = {
                pair_key: prediction
                for pair_key, prediction
                in prediction_by_pair.items()
                if (
                    pair_key[0]
                    in component_key_set
                    and pair_key[1]
                    in component_key_set
                    and is_valid_grouping_edge(
                        prediction
                    )
                )
            }

            component_accounts = [
                account_by_key[key]
                for key
                in component_keys
            ]

            primary_account = (
                select_primary_account(
                    component_accounts,
                    component_predictions,
                )
            )

            primary_key = (
                get_account_identity(
                    primary_account
                )
            )

            duplicate_entries: list[
                dict[str, Any]
            ] = []

            for candidate_account in (
                component_accounts
            ):
                candidate_key = (
                    get_account_identity(
                        candidate_account
                    )
                )

                if (
                    candidate_key
                    == primary_key
                ):
                    continue

                pair_key = tuple(
                    sorted(
                        (
                            primary_key,
                            candidate_key,
                        )
                    )
                )

                prediction = (
                    component_predictions.get(
                        pair_key
                    )
                )

                if prediction is None:
                    continue

                duplicate_entries.append(
                    build_candidate_entry(
                        candidate_number=(
                            len(
                                duplicate_entries
                            )
                            + 1
                        ),
                        account=(
                            candidate_account
                        ),
                        prediction=(
                            prediction
                        ),
                    )
                )

            if not duplicate_entries:
                continue

            duplicate_entries.sort(
                key=lambda item: (
                    -float(
                        item[
                            "confidence"
                        ]
                    ),
                    normalize_key_part(
                        (
                            item.get(
                                "account"
                            )
                            or {}
                        ).get(
                            "username"
                        )
                    ),
                )
            )

            for index, entry in enumerate(
                duplicate_entries,
                start=1,
            ):
                entry[
                    "id"
                ] = index

            highest_confidence = max(
                float(
                    entry[
                        "confidence"
                    ]
                )
                for entry
                in duplicate_entries
            )

            results[
                application
            ].append(
                {
                    "groupId": group_id,
                    "primaryAccount": (
                        primary_account.username
                    ),
                    "duplicates": len(
                        duplicate_entries
                    ),
                    "highestConfidence": (
                        highest_confidence
                    ),
                }
            )

            details[
                group_id
            ] = {
                "primaryAccount": (
                    primary_account.model_dump()
                ),
                "duplicates": (
                    duplicate_entries
                ),
            }

            group_id += 1

    for application in results:
        results[
            application
        ].sort(
            key=lambda item: (
                -float(
                    item[
                        "highestConfidence"
                    ]
                ),
                normalize_key_part(
                    item[
                        "primaryAccount"
                    ]
                ),
            )
        )

    print(
        "[Duplicate Detection] "
        "All applications completed."
    )

    return (
        dict(results),
        details,
    )