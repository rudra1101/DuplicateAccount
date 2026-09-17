from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db_models.application import ApplicationRecord
from app.db_models.application_schema import ApplicationSchemaRecord
from app.db_models.schema_attribute import SchemaAttributeRecord
from app.models.account import Account


MIN_PAIR_SCORE = 45.0


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _raw_value(raw: dict[str, Any], attribute: str) -> Any:
    target = _key(attribute)
    for name, value in raw.items():
        if _key(name) == target:
            return value
    return None


def _normalized(value: Any, normalization: str | None) -> str:
    text = str(value or "").strip()
    mode = str(normalization or "NONE").upper()
    if not text:
        return ""
    if mode in {"LOWERCASE", "EMAIL", "NAME"}:
        return text.casefold()
    if mode == "UPPERCASE":
        return text.upper()
    if mode == "ALPHANUMERIC":
        return "".join(ch for ch in text.casefold() if ch.isalnum())
    if mode == "PHONE":
        return "".join(ch for ch in text if ch.isdigit())
    return text.strip()


def _policies(db: Session, integration_id: int) -> dict[str, list[SchemaAttributeRecord]]:
    apps = list(
        db.scalars(
            select(ApplicationRecord)
            .options(
                selectinload(ApplicationRecord.schemas)
                .selectinload(ApplicationSchemaRecord.attributes)
            )
            .where(ApplicationRecord.integration_id == integration_id)
        ).all()
    )
    result: dict[str, list[SchemaAttributeRecord]] = {}
    for app in apps:
        schema = next((item for item in app.schemas if item.is_active), None)
        if schema is None:
            continue
        attrs = [
            attr
            for attr in schema.attributes
            if attr.use_for_matching and float(attr.match_weight or 0) > 0
        ]
        if attrs:
            result[app.name.strip().lower()] = attrs
    return result


def detect_schema_duplicate_results(
    db: Session,
    *,
    integration_id: int,
    accounts: list[Account],
    starting_group_id: int = 1,
) -> tuple[dict[str, list[dict[str, Any]]], dict[int, dict[str, Any]]]:
    """Find deterministic duplicate evidence from each application's saved schema policy.

    The existing AI detector remains in place. This pass makes schema-selected source
    attributes (including arbitrary raw attributes) first-class duplicate evidence.
    """
    policies = _policies(db, integration_id)
    by_application: dict[str, list[Account]] = defaultdict(list)
    for account in accounts:
        by_application[str(account.application or "Unknown")].append(account)

    groups_by_app: dict[str, list[dict[str, Any]]] = {}
    details: dict[int, dict[str, Any]] = {}
    group_id = starting_group_id

    for application, app_accounts in by_application.items():
        attributes = policies.get(application.strip().lower())
        if not attributes or len(app_accounts) < 2:
            continue

        edges: dict[tuple[int, int], dict[str, Any]] = {}
        for left_index, right_index in combinations(range(len(app_accounts)), 2):
            left = app_accounts[left_index]
            right = app_accounts[right_index]
            if left.id and right.id and str(left.id) == str(right.id):
                continue

            score = 0.0
            matched: list[str] = []
            different: list[str] = []
            evidence: list[dict[str, Any]] = []
            for attribute in attributes:
                left_value = _raw_value(left.rawAttributes or {}, attribute.name)
                right_value = _raw_value(right.rawAttributes or {}, attribute.name)
                left_norm = _normalized(left_value, attribute.normalization_type)
                right_norm = _normalized(right_value, attribute.normalization_type)
                if not left_norm or not right_norm:
                    continue
                if left_norm == right_norm:
                    weight = float(attribute.match_weight or 0)
                    score += weight
                    matched.append(attribute.name)
                    evidence.append({
                        "attribute": attribute.name,
                        "weight": round(weight, 2),
                        "value": str(left_value),
                        "normalization": attribute.normalization_type,
                    })
                else:
                    different.append(attribute.name)

            if score >= MIN_PAIR_SCORE and matched:
                edges[(left_index, right_index)] = {
                    "score": min(100.0, score),
                    "matched": matched,
                    "different": different,
                    "evidence": evidence,
                }

        if not edges:
            continue

        parent = list(range(len(app_accounts)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left_index, right_index in edges:
            union(left_index, right_index)

        components: dict[int, list[int]] = defaultdict(list)
        for index in range(len(app_accounts)):
            components[find(index)].append(index)

        app_groups: list[dict[str, Any]] = []
        for indexes in components.values():
            if len(indexes) < 2:
                continue
            primary_index = indexes[0]
            primary = app_accounts[primary_index]
            candidates: list[dict[str, Any]] = []
            highest = 0.0

            for candidate_index in indexes[1:]:
                pair = tuple(sorted((primary_index, candidate_index)))
                pair_evidence = edges.get(pair)
                if pair_evidence is None:
                    best = None
                    for other_index in indexes:
                        if other_index == candidate_index:
                            continue
                        possible = edges.get(tuple(sorted((other_index, candidate_index))))
                        if possible and (best is None or possible["score"] > best["score"]):
                            best = possible
                    pair_evidence = best
                if pair_evidence is None:
                    continue

                confidence = float(pair_evidence["score"])
                highest = max(highest, confidence)
                candidates.append({
                    "id": len(candidates) + 1,
                    "confidence": confidence,
                    "recommendation": "MERGE" if confidence >= 70 else "REVIEW",
                    "matchedAttributes": pair_evidence["matched"],
                    "differentAttributes": pair_evidence["different"],
                    "account": app_accounts[candidate_index].model_dump(),
                    "classification": "SCHEMA_POLICY_MATCH",
                    "modelVersion": "schema-policy-v1",
                    "groupingEvidence": "SCHEMA_POLICY",
                    "reasons": [
                        "Matched source attributes selected by the application's generated matching policy."
                    ],
                    "warnings": [],
                    "features": {"schemaEvidence": pair_evidence["evidence"]},
                })

            if not candidates:
                continue

            app_groups.append({
                "groupId": group_id,
                "primaryAccount": primary.username,
                "duplicates": len(candidates),
                "highestConfidence": highest,
            })
            details[group_id] = {
                "primaryAccount": primary.model_dump(),
                "duplicates": candidates,
            }
            group_id += 1

        if app_groups:
            groups_by_app[application] = app_groups

    return groups_by_app, details
