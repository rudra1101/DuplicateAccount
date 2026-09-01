from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.remediation_item import RemediationItemRecord
from app.db_models.scan import ScanRecord
from app.services.review_pair_feedback_service import load_pair_feedback, normalize_pair_keys
from app.services.review_service import (
    get_duplicate_group_details as get_raw_duplicate_group_details,
    get_duplicate_groups as get_raw_duplicate_groups,
    get_review_summary as get_raw_review_summary,
)


ACTIVE_REMEDIATION_STATUSES = {
    "PENDING_ACTION",
    "TICKET_OPEN",
    "ACTIONED",
    "FAILED",
}


def _normalize_key_part(value: Any) -> str:
    return str(value or "").strip().lower()


def _account_key(*, application: str, account: dict[str, Any], fallback_username: str = "") -> str:
    normalized_application = _normalize_key_part(application or "Unknown")
    source_id = _normalize_key_part(account.get("id"))
    if source_id:
        return f"{normalized_application}:{source_id}"
    username = _normalize_key_part(account.get("username") or fallback_username)
    return f"{normalized_application}:username:{username}"


def _integration_id_for_scan(db: Session, scan_id: int) -> int | None:
    scan = db.get(ScanRecord, scan_id)
    if scan is None or scan.integration_id is None:
        return None
    return int(scan.integration_id)


def _remediation_by_pair(
    db: Session,
    *,
    integration_id: int,
    application: str,
) -> dict[tuple[str, str], RemediationItemRecord]:
    records = list(
        db.scalars(
            select(RemediationItemRecord).where(
                RemediationItemRecord.integration_id == integration_id,
                RemediationItemRecord.application == application,
            )
        ).all()
    )
    return {
        normalize_pair_keys(record.account_1_key, record.account_2_key): record
        for record in records
    }


def _candidate_is_visible(
    *,
    application: str,
    primary_account: dict[str, Any],
    candidate: dict[str, Any],
    remediation_by_pair: dict[tuple[str, str], RemediationItemRecord],
    durable_feedback: dict[tuple[str, str, str], str],
) -> bool:
    candidate_account = candidate.get("account") or {}
    primary_key = _account_key(
        application=application,
        account=primary_account,
        fallback_username=str(primary_account.get("username") or ""),
    )
    candidate_key = _account_key(
        application=str(candidate_account.get("application") or application),
        account=candidate_account,
        fallback_username=str(candidate_account.get("username") or ""),
    )
    key_1, key_2 = normalize_pair_keys(primary_key, candidate_key)

    remediation = remediation_by_pair.get((key_1, key_2))
    durable_decision = durable_feedback.get((application, key_1, key_2))

    if remediation is not None:
        if remediation.status in ACTIVE_REMEDIATION_STATUSES:
            return False
        if remediation.status == "IGNORED":
            # Manual remediation Ignore clears durable DUPLICATE feedback and
            # intentionally returns the pair to review. NOT_DUPLICATE remains
            # durable and therefore stays out of the active queue.
            return durable_decision != "NOT_DUPLICATE"

    if durable_decision in {"DUPLICATE", "NOT_DUPLICATE"}:
        return False

    current_decision = str(candidate.get("reviewDecision") or "").strip().upper()
    if current_decision in {"DUPLICATE", "NOT_DUPLICATE"}:
        return False

    return True


def get_visible_duplicate_group_details(
    db: Session,
    *,
    group_id: int,
    integration_id: int | None = None,
) -> dict[str, Any] | None:
    details = get_raw_duplicate_group_details(
        db=db,
        group_id=group_id,
        integration_id=integration_id,
    )
    if details is None:
        return None

    resolved_integration_id = integration_id or _integration_id_for_scan(db, int(details["scanId"]))
    if resolved_integration_id is None:
        # Legacy scans without integration identity cannot safely use durable
        # pair state, so preserve the historical Review Queue behavior.
        return details

    application = str(details.get("application") or "Unknown")
    remediation_by_pair = _remediation_by_pair(
        db,
        integration_id=resolved_integration_id,
        application=application,
    )
    durable_feedback = load_pair_feedback(db, integration_id=resolved_integration_id)
    primary_account = details.get("primaryAccount") or {}

    visible_candidates = [
        candidate
        for candidate in details.get("duplicates") or []
        if _candidate_is_visible(
            application=application,
            primary_account=primary_account,
            candidate=candidate,
            remediation_by_pair=remediation_by_pair,
            durable_feedback=durable_feedback,
        )
    ]

    result = dict(details)
    result["duplicates"] = visible_candidates
    result["highestConfidence"] = (
        max(float(candidate.get("confidence") or 0) for candidate in visible_candidates)
        if visible_candidates
        else 0
    )
    return result


def get_visible_duplicate_groups(
    db: Session,
    *,
    application: str,
    integration_id: int | None = None,
) -> list[dict[str, Any]]:
    raw_groups = get_raw_duplicate_groups(
        db=db,
        application=application,
        integration_id=integration_id,
    )
    visible_groups: list[dict[str, Any]] = []

    for group in raw_groups:
        details = get_visible_duplicate_group_details(
            db,
            group_id=int(group["groupId"]),
            integration_id=integration_id,
        )
        if details is None:
            continue
        visible_candidates = details.get("duplicates") or []
        if not visible_candidates:
            continue
        visible_groups.append(
            {
                **group,
                "duplicates": len(visible_candidates),
                "highestConfidence": max(
                    float(candidate.get("confidence") or 0)
                    for candidate in visible_candidates
                ),
            }
        )

    return visible_groups


def get_visible_review_summary(
    db: Session,
    *,
    integration_id: int | None = None,
) -> list[dict[str, Any]]:
    cards = get_raw_review_summary(db=db, integration_id=integration_id)
    visible_cards: list[dict[str, Any]] = []

    for card in cards:
        card_integration_id = card.get("integrationId")
        groups = get_visible_duplicate_groups(
            db,
            application=str(card.get("application") or "Unknown"),
            integration_id=(
                int(card_integration_id)
                if card_integration_id is not None
                else integration_id
            ),
        )
        duplicate_accounts = sum(int(group.get("duplicates") or 0) for group in groups)
        high_confidence = sum(
            1
            for group in groups
            if float(group.get("highestConfidence") or 0) >= 95
        )
        visible_cards.append(
            {
                **card,
                "duplicateGroups": len(groups),
                "duplicateAccounts": duplicate_accounts,
                "highConfidence": high_confidence,
            }
        )

    return visible_cards
