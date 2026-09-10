from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db_models.account import AccountRecord
from app.db_models.identity import IdentityRecord
from app.db_models.orphan_finding import OrphanFindingRecord


ACTIVE_STATUSES = {"active", "enabled", "true", "1", "yes"}
TERMINATED_STATUSES = {"terminated", "inactive", "disabled", "former", "left", "leaver"}
NON_HUMAN_HINTS = ("svc", "service", "shared", "admin", "breakglass", "robot", "rpa", "system")


@dataclass(frozen=True)
class CorrelationResult:
    identity: IdentityRecord | None
    method: str | None


def _norm(value: str | None) -> str:
    return str(value or "").strip().lower()


def _looks_non_human(account: AccountRecord) -> bool:
    username = _norm(account.username)
    display_name = _norm(account.display_name)
    raw = account.raw_attributes or {}
    account_type = _norm(
        raw.get("accountType")
        or raw.get("account_type")
        or raw.get("type")
        or raw.get("userType")
    )
    if account_type in {"service", "shared", "system", "robot", "rpa"}:
        return True
    return any(hint in username or hint in display_name for hint in NON_HUMAN_HINTS)


def _has_valid_non_human_owner(account: AccountRecord) -> bool:
    raw = account.raw_attributes or {}
    owner = (
        raw.get("owner")
        or raw.get("ownerId")
        or raw.get("owner_id")
        or raw.get("serviceOwner")
        or raw.get("service_owner")
    )
    return bool(str(owner or "").strip())


def _indexes(identities: Iterable[IdentityRecord]):
    employee: dict[str, IdentityRecord] = {}
    email: dict[str, IdentityRecord] = {}
    username: dict[str, IdentityRecord] = {}
    for identity in identities:
        if _norm(identity.employee_id):
            employee.setdefault(_norm(identity.employee_id), identity)
        if _norm(identity.email):
            email.setdefault(_norm(identity.email), identity)
        if _norm(identity.username):
            username.setdefault(_norm(identity.username), identity)
    return employee, email, username


def correlate_account(
    account: AccountRecord,
    *,
    employee_index: dict[str, IdentityRecord],
    email_index: dict[str, IdentityRecord],
    username_index: dict[str, IdentityRecord],
) -> CorrelationResult:
    employee_id = _norm(account.employee_id)
    if employee_id and employee_id in employee_index:
        return CorrelationResult(employee_index[employee_id], "EMPLOYEE_ID_EXACT")

    email = _norm(account.email)
    if email and email in email_index:
        return CorrelationResult(email_index[email], "EMAIL_EXACT")

    username = _norm(account.username)
    if username and username in username_index:
        return CorrelationResult(username_index[username], "USERNAME_EXACT")

    return CorrelationResult(None, None)


def _severity(risk_score: float) -> str:
    if risk_score >= 90:
        return "CRITICAL"
    if risk_score >= 70:
        return "HIGH"
    if risk_score >= 40:
        return "MEDIUM"
    return "LOW"


def _risk_for(account: AccountRecord, *, orphan_type: str) -> float:
    score = 45.0
    status = _norm(account.status)
    raw = account.raw_attributes or {}

    if status in ACTIVE_STATUSES or not status:
        score += 20
    if orphan_type == "TERMINATED_IDENTITY":
        score += 15

    privileged = raw.get("privileged") or raw.get("isPrivileged") or raw.get("admin")
    groups = str(raw.get("groups") or raw.get("memberOf") or "").lower()
    if str(privileged).strip().lower() in ACTIVE_STATUSES:
        score += 25
    if any(term in groups for term in ("domain admins", "enterprise admins", "administrators", "sudo")):
        score += 25

    return min(score, 100.0)


def detect_orphan_findings(db: Session, *, scan_id: int) -> list[OrphanFindingRecord]:
    accounts = list(
        db.scalars(select(AccountRecord).where(AccountRecord.scan_id == scan_id)).all()
    )
    identities = list(db.scalars(select(IdentityRecord)).all())
    employee_index, email_index, username_index = _indexes(identities)

    db.execute(delete(OrphanFindingRecord).where(OrphanFindingRecord.scan_id == scan_id))
    findings: list[OrphanFindingRecord] = []

    for account in accounts:
        correlation = correlate_account(
            account,
            employee_index=employee_index,
            email_index=email_index,
            username_index=username_index,
        )

        if correlation.identity is not None:
            employment_status = _norm(correlation.identity.employment_status)
            if employment_status not in TERMINATED_STATUSES:
                continue
            orphan_type = "TERMINATED_IDENTITY"
            confidence = 100.0
            evidence = {
                "reason": "Account is correlated to an authoritative identity that is terminated or inactive.",
                "identityStatus": correlation.identity.employment_status,
                "correlationMethod": correlation.method,
            }
        else:
            if _looks_non_human(account) and _has_valid_non_human_owner(account):
                continue
            orphan_type = "UNMATCHED_ACCOUNT"
            confidence = 98.0 if account.employee_id else 90.0
            evidence = {
                "reason": "No matching authoritative identity was found.",
                "employeeIdPresent": bool(account.employee_id),
                "nonHumanAccountSuspected": _looks_non_human(account),
                "ownerPresent": _has_valid_non_human_owner(account),
            }

        risk_score = _risk_for(account, orphan_type=orphan_type)
        finding = OrphanFindingRecord(
            scan_id=scan_id,
            account_id=account.id,
            orphan_type=orphan_type,
            confidence=confidence,
            risk_score=risk_score,
            severity=_severity(risk_score),
            correlation_method=correlation.method,
            matched_identity_id=correlation.identity.id if correlation.identity else None,
            evidence=evidence,
        )
        db.add(finding)
        findings.append(finding)

    db.commit()
    for finding in findings:
        db.refresh(finding)
    return findings
