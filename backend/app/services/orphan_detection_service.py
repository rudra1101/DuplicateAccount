from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db_models.account import AccountRecord
from app.db_models.correlation_policy import CorrelationPolicyRecord, CorrelationRuleRecord
from app.db_models.identity import IdentityRecord
from app.db_models.orphan_finding import OrphanFindingRecord
from app.db_models.scan import ScanRecord
from app.services.correlation_policy_service import get_policy_for_account_integration


ACTIVE_STATUSES = {"active", "enabled", "true", "1", "yes"}
TERMINATED_STATUSES = {"terminated", "inactive", "disabled", "former", "left", "leaver"}
NON_HUMAN_HINTS = ("svc", "service", "shared", "admin", "breakglass", "robot", "rpa", "system")

ACCOUNT_CANONICAL_FIELDS = {
    "id": "source_account_id",
    "sourceaccountid": "source_account_id",
    "username": "username",
    "displayname": "display_name",
    "email": "email",
    "employeeid": "employee_id",
    "department": "department",
    "manager": "manager",
    "status": "status",
    "created": "created",
    "application": "application",
}
IDENTITY_CANONICAL_FIELDS = {
    "id": "source_identity_id",
    "sourceidentityid": "source_identity_id",
    "username": "username",
    "displayname": "display_name",
    "email": "email",
    "employeeid": "employee_id",
    "department": "department",
    "manager": "manager",
    "employmentstatus": "employment_status",
    "status": "employment_status",
}


@dataclass(frozen=True)
class CorrelationResult:
    identity: IdentityRecord | None
    method: str | None
    confidence: float
    attempts: list[dict[str, Any]]
    ambiguous: bool = False


def _field_key(value: str) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalized_match_value(value: Any) -> str:
    return "".join(ch for ch in _norm(value) if ch.isalnum())


def _raw_value(raw: dict[str, Any], attribute: str) -> Any:
    target = _field_key(attribute)
    for key, value in raw.items():
        if _field_key(str(key)) == target:
            return value
    return None


def _account_value(account: AccountRecord, attribute: str) -> Any:
    canonical = ACCOUNT_CANONICAL_FIELDS.get(_field_key(attribute))
    if canonical:
        return getattr(account, canonical, None)
    return _raw_value(account.raw_attributes or {}, attribute)


def _identity_value(identity: IdentityRecord, attribute: str) -> Any:
    canonical = IDENTITY_CANONICAL_FIELDS.get(_field_key(attribute))
    if canonical:
        return getattr(identity, canonical, None)
    return _raw_value(identity.raw_attributes or {}, attribute)


def _values_match(account_value: Any, identity_value: Any, match_type: str) -> bool:
    left = str(account_value or "").strip()
    right = str(identity_value or "").strip()
    if not left or not right:
        return False
    match_type = match_type.upper()
    if match_type == "EXACT":
        return left == right
    if match_type == "CASE_INSENSITIVE":
        return left.casefold() == right.casefold()
    if match_type == "NORMALIZED":
        return _normalized_match_value(left) == _normalized_match_value(right)
    raise ValueError(f"Unsupported correlation match type: {match_type}")


def _match_confidence(match_type: str) -> float:
    return {"EXACT": 100.0, "CASE_INSENSITIVE": 98.0, "NORMALIZED": 95.0}.get(
        match_type.upper(), 90.0
    )


def correlate_account(
    account: AccountRecord,
    *,
    identities: list[IdentityRecord],
    policy: CorrelationPolicyRecord,
) -> CorrelationResult:
    attempts: list[dict[str, Any]] = []
    rules = sorted((rule for rule in policy.rules if rule.enabled), key=lambda rule: rule.priority)

    for rule in rules:
        account_value = _account_value(account, rule.account_attribute)
        if account_value is None or not str(account_value).strip():
            attempts.append(
                {
                    "priority": rule.priority,
                    "accountAttribute": rule.account_attribute,
                    "identityAttribute": rule.identity_attribute,
                    "matchType": rule.match_type,
                    "accountValue": None,
                    "result": "ACCOUNT_VALUE_MISSING",
                }
            )
            continue

        matches = [
            identity
            for identity in identities
            if _values_match(
                account_value,
                _identity_value(identity, rule.identity_attribute),
                rule.match_type,
            )
        ]
        attempt = {
            "priority": rule.priority,
            "accountAttribute": rule.account_attribute,
            "identityAttribute": rule.identity_attribute,
            "matchType": rule.match_type,
            "accountValue": str(account_value),
            "matches": len(matches),
        }

        if len(matches) == 1:
            attempt["result"] = "MATCHED"
            attempts.append(attempt)
            method = (
                f"{rule.account_attribute}->{rule.identity_attribute}:"
                f"{rule.match_type}"
            )
            return CorrelationResult(
                identity=matches[0],
                method=method,
                confidence=_match_confidence(rule.match_type),
                attempts=attempts,
            )

        if len(matches) > 1:
            attempt["result"] = "AMBIGUOUS"
            attempts.append(attempt)
            return CorrelationResult(
                identity=None,
                method=None,
                confidence=0.0,
                attempts=attempts,
                ambiguous=True,
            )

        attempt["result"] = "NO_MATCH"
        attempts.append(attempt)

    return CorrelationResult(None, None, 0.0, attempts)


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
    if orphan_type == "AMBIGUOUS_CORRELATION":
        score += 10

    privileged = raw.get("privileged") or raw.get("isPrivileged") or raw.get("admin")
    groups = str(raw.get("groups") or raw.get("memberOf") or "").lower()
    if str(privileged).strip().lower() in ACTIVE_STATUSES:
        score += 25
    if any(term in groups for term in ("domain admins", "enterprise admins", "administrators", "sudo")):
        score += 25
    return min(score, 100.0)


def detect_orphan_findings(db: Session, *, scan_id: int) -> list[OrphanFindingRecord]:
    scan = db.get(ScanRecord, scan_id)
    if scan is None:
        raise ValueError("Scan not found.")
    if scan.integration_id is None:
        raise ValueError("The scan is not linked to an account integration.")

    policy = get_policy_for_account_integration(db, scan.integration_id)
    if policy is None:
        raise ValueError(
            "No enabled correlation policy is configured for this account integration."
        )

    accounts = list(
        db.scalars(select(AccountRecord).where(AccountRecord.scan_id == scan_id)).all()
    )
    identities = list(
        db.scalars(
            select(IdentityRecord).where(
                IdentityRecord.integration_id == policy.authoritative_integration_id
            )
        ).all()
    )
    if not identities:
        raise ValueError(
            "The authoritative source selected by the correlation policy has no identities loaded."
        )

    db.execute(delete(OrphanFindingRecord).where(OrphanFindingRecord.scan_id == scan_id))
    findings: list[OrphanFindingRecord] = []

    for account in accounts:
        correlation = correlate_account(account, identities=identities, policy=policy)

        if correlation.identity is not None:
            employment_status = _norm(correlation.identity.employment_status)
            if employment_status not in TERMINATED_STATUSES:
                continue
            orphan_type = "TERMINATED_IDENTITY"
            confidence = correlation.confidence
            evidence = {
                "reason": "Account correlated to an authoritative identity that is terminated or inactive.",
                "policyId": policy.id,
                "policyName": policy.name,
                "identityStatus": correlation.identity.employment_status,
                "correlationMethod": correlation.method,
                "correlationAttempts": correlation.attempts,
            }
        else:
            if _looks_non_human(account) and _has_valid_non_human_owner(account):
                continue
            orphan_type = "AMBIGUOUS_CORRELATION" if correlation.ambiguous else "UNMATCHED_ACCOUNT"
            confidence = 80.0 if correlation.ambiguous else 95.0
            evidence = {
                "reason": (
                    "Correlation rule matched multiple authoritative identities."
                    if correlation.ambiguous
                    else "No configured correlation rule matched an authoritative identity."
                ),
                "policyId": policy.id,
                "policyName": policy.name,
                "strategy": policy.strategy,
                "correlationAttempts": correlation.attempts,
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
