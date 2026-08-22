from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.account import AccountRecord
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.scan import ScanRecord
from app.services.review_pair_feedback_service import (
    load_pair_feedback,
    normalize_pair_keys,
    upsert_pair_feedback,
)
from app.services.review_service import save_candidate_decision


def _normalize_key_part(value: Any) -> str:
    return str(value or "").strip().lower()


def _account_key(*, application: str, source_id: Any, username: Any) -> str:
    app = _normalize_key_part(application or "Unknown")
    account_id = _normalize_key_part(source_id)
    if account_id:
        return f"{app}:{account_id}"
    return f"{app}:username:{_normalize_key_part(username)}"


def _primary_account_key(
    db: Session,
    *,
    group: DuplicateGroupRecord,
) -> str:
    account = db.scalars(
        select(AccountRecord)
        .where(
            AccountRecord.scan_id == group.scan_id,
            AccountRecord.application == group.application,
            AccountRecord.username == group.primary_username,
        )
        .order_by(AccountRecord.id.asc())
        .limit(1)
    ).first()

    return _account_key(
        application=group.application,
        source_id=account.source_account_id if account is not None else None,
        username=group.primary_username,
    )


def _candidate_account_key(
    *,
    group: DuplicateGroupRecord,
    candidate: DuplicateCandidateRecord,
) -> str:
    data = candidate.account_data or {}
    return _account_key(
        application=str(data.get("application") or group.application),
        source_id=data.get("id"),
        username=data.get("username") or candidate.username,
    )


def _pair_context(
    db: Session,
    *,
    candidate_id: int,
) -> tuple[DuplicateCandidateRecord, DuplicateGroupRecord, ScanRecord, str, str]:
    candidate = db.get(DuplicateCandidateRecord, candidate_id)
    if candidate is None:
        raise ValueError("Duplicate candidate was not found.")

    group = db.get(DuplicateGroupRecord, candidate.group_id)
    if group is None:
        raise ValueError("Duplicate group was not found.")

    scan = db.get(ScanRecord, group.scan_id)
    if scan is None or scan.integration_id is None:
        raise ValueError(
            "Duplicate group is not attached to an integration scan, so durable feedback cannot be resolved."
        )

    primary_key = _primary_account_key(db, group=group)
    candidate_key = _candidate_account_key(group=group, candidate=candidate)
    return candidate, group, scan, primary_key, candidate_key


def save_duplicate_group_candidate_decision(
    db: Session,
    *,
    candidate_id: int,
    decision: str,
    comment: str | None = None,
    reviewer_name: str | None = None,
) -> dict[str, Any]:
    """Save the existing group decision and persist it as pair feedback."""
    result = save_candidate_decision(
        db=db,
        candidate_id=candidate_id,
        decision=decision,
        comment=comment,
        reviewer_name=reviewer_name,
    )

    _candidate, group, scan, primary_key, candidate_key = _pair_context(
        db,
        candidate_id=candidate_id,
    )

    upsert_pair_feedback(
        db,
        integration_id=int(scan.integration_id),
        application=group.application,
        account_1_key=primary_key,
        account_2_key=candidate_key,
        decision=str(result.get("decision") or decision),
        comment=result.get("comment"),
        reviewer_name=result.get("reviewerName"),
        source_review_candidate_id=None,
    )
    db.commit()

    print(
        "[Reviewer Feedback] "
        f"Integration={scan.integration_id}, "
        f"Application={group.application}, "
        f"Pair={primary_key} <-> {candidate_key}, "
        f"Decision={str(result.get('decision') or decision).upper()}, "
        "Source=DUPLICATE_GROUP"
    )

    return result


def get_duplicate_group_candidate_durable_decision(
    db: Session,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """Return the durable pair decision for a duplicate-group candidate."""
    _candidate, group, scan, primary_key, candidate_key = _pair_context(
        db,
        candidate_id=candidate_id,
    )
    key_1, key_2 = normalize_pair_keys(primary_key, candidate_key)
    feedback = load_pair_feedback(
        db,
        integration_id=int(scan.integration_id),
    )
    decision = feedback.get((group.application, key_1, key_2))
    return {
        "candidateId": candidate_id,
        "decision": decision,
        "account1Key": key_1,
        "account2Key": key_2,
    }
