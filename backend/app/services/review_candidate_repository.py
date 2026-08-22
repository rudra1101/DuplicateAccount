from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.review_candidate import ReviewCandidateRecord
from app.db_models.scan import ScanRecord


VALID_REVIEW_DECISIONS = {"DUPLICATE", "NOT_DUPLICATE", "UNCERTAIN"}


def save_review_candidates(
    db: Session,
    *,
    scan_id: int,
    candidates: list[dict[str, Any]],
) -> int:
    saved = 0
    for candidate in candidates:
        account_1 = candidate.get("account1") or {}
        account_2 = candidate.get("account2") or {}
        application = str(
            account_1.get("application")
            or account_2.get("application")
            or "Unknown"
        ).strip()

        record = ReviewCandidateRecord(
            scan_id=scan_id,
            application=application,
            account_1_key=str(candidate.get("account1Key") or ""),
            account_2_key=str(candidate.get("account2Key") or ""),
            account_1_data=account_1,
            account_2_data=account_2,
            confidence=float(candidate.get("confidence") or 0),
            classification=candidate.get("classification"),
            review_reason=str(candidate.get("reviewReason") or "REVIEW"),
            model_version=candidate.get("modelVersion"),
            matched_attributes=candidate.get("matchedAttributes") or [],
            conflicting_attributes=candidate.get("conflictingAttributes") or [],
            features=candidate.get("features") or {},
            reasons=candidate.get("reasons") or [],
            warnings=candidate.get("warnings") or [],
        )
        db.add(record)
        saved += 1

    db.commit()
    return saved


def latest_scan_id_for_integration(
    db: Session,
    integration_id: int | None,
) -> int | None:
    query = select(ScanRecord.id).where(ScanRecord.status == "COMPLETED")
    if integration_id is not None:
        query = query.where(ScanRecord.integration_id == integration_id)
    query = query.order_by(ScanRecord.id.desc()).limit(1)
    return db.scalar(query)


def list_review_candidates(
    db: Session,
    *,
    integration_id: int | None = None,
    application: str | None = None,
    decision: str | None = None,
) -> list[dict[str, Any]]:
    scan_id = latest_scan_id_for_integration(db, integration_id)
    if scan_id is None:
        return []

    query = select(ReviewCandidateRecord).where(ReviewCandidateRecord.scan_id == scan_id)
    if application:
        query = query.where(ReviewCandidateRecord.application == application)
    if decision:
        normalized = decision.strip().upper()
        if normalized == "PENDING":
            query = query.where(ReviewCandidateRecord.review_decision.is_(None))
        else:
            query = query.where(ReviewCandidateRecord.review_decision == normalized)

    records = list(
        db.scalars(
            query.order_by(
                ReviewCandidateRecord.confidence.desc(),
                ReviewCandidateRecord.id.asc(),
            )
        ).all()
    )
    return [review_candidate_to_dict(record) for record in records]


def review_candidate_to_dict(record: ReviewCandidateRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "scanId": record.scan_id,
        "application": record.application,
        "account1Key": record.account_1_key,
        "account2Key": record.account_2_key,
        "account1": record.account_1_data,
        "account2": record.account_2_data,
        "confidence": record.confidence,
        "classification": record.classification,
        "reviewReason": record.review_reason,
        "modelVersion": record.model_version,
        "matchedAttributes": record.matched_attributes,
        "conflictingAttributes": record.conflicting_attributes,
        "features": record.features,
        "reasons": record.reasons,
        "warnings": record.warnings,
        "reviewDecision": record.review_decision,
        "reviewComment": record.review_comment,
        "reviewerName": record.reviewer_name,
        "reviewedAt": record.reviewed_at.isoformat() if record.reviewed_at else None,
    }


def save_review_candidate_decision(
    db: Session,
    *,
    candidate_id: int,
    decision: str,
    comment: str | None = None,
    reviewer_name: str | None = None,
) -> dict[str, Any]:
    record = db.get(ReviewCandidateRecord, candidate_id)
    if record is None:
        raise ValueError("Review candidate not found.")

    normalized = decision.strip().upper()
    if normalized not in VALID_REVIEW_DECISIONS:
        raise ValueError(
            "Decision must be one of: DUPLICATE, NOT_DUPLICATE, UNCERTAIN."
        )

    record.review_decision = normalized
    record.review_comment = (comment or "").strip() or None
    record.reviewer_name = (reviewer_name or "").strip() or None
    record.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return review_candidate_to_dict(record)
