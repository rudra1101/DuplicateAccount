from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.services.orphan_account_service import list_orphan_accounts


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _account_label(account: dict[str, Any]) -> str:
    return str(
        account.get("displayName")
        or account.get("username")
        or account.get("nativeIdentity")
        or account.get("employeeId")
        or account.get("sourceAccountId")
        or "Account"
    )


def _identity_label(identity: dict[str, Any]) -> str:
    return str(
        identity.get("displayName")
        or identity.get("username")
        or identity.get("email")
        or identity.get("employeeId")
        or identity.get("sourceIdentityId")
        or identity.get("id")
        or "Identity"
    )


def _matched_identities(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for attempt in attempts:
        candidates = attempt.get("matchedIdentities")
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            key = str(
                candidate.get("id")
                or candidate.get("sourceIdentityId")
                or candidate.get("employeeId")
                or candidate.get("username")
                or candidate.get("email")
                or ""
            ).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(candidate)
    return results


def _attempt_line(attempt: dict[str, Any], index: int) -> str:
    priority = attempt.get("priority")
    order = priority if priority not in (None, "") else index
    account_attribute = _clean(attempt.get("accountAttribute")) or "account attribute"
    identity_attribute = _clean(attempt.get("identityAttribute")) or "identity attribute"
    match_type = _clean(attempt.get("matchType")) or "configured match"
    result = (_clean(attempt.get("result")) or "UNKNOWN").upper()
    account_value = _clean(attempt.get("accountValue"))
    matches = attempt.get("matches")

    rule = (
        f"{order}. `{account_attribute}` → `{identity_attribute}` "
        f"using **{match_type}**"
    )
    if result == "ACCOUNT_VALUE_MISSING":
        return f"{rule} — **ACCOUNT_VALUE_MISSING**; the source account had no value to compare."
    if result == "NO_MATCH":
        value = f"`{account_value}`" if account_value is not None else "the source value"
        return f"{rule} — **NO_MATCH**; {value} matched 0 authoritative identities."
    if result == "AMBIGUOUS":
        match_count = matches if matches not in (None, "") else "multiple"
        return f"{rule} — **AMBIGUOUS**; the value matched {match_count} authoritative identities."
    if result == "MATCHED":
        value = f"`{account_value}`" if account_value is not None else "the source value"
        return f"{rule} — **MATCHED**; {value} matched exactly one authoritative identity."

    suffix = f"; matches: {matches}" if matches not in (None, "") else ""
    return f"{rule} — **{result}**{suffix}."


def _format_explanation(account: dict[str, Any]) -> str:
    label = _account_label(account)
    employee_id = _clean(account.get("employeeId"))
    username = _clean(account.get("username")) or _clean(account.get("nativeIdentity"))
    application = _clean(account.get("application"))
    integration = _clean(account.get("integrationName"))
    orphan_type = _clean(account.get("orphanType")) or "UNKNOWN"
    orphan_status = _clean(account.get("orphanStatus"))
    reason = _clean(account.get("reason")) or "No persisted orphan reason is available."
    policy_name = _clean(account.get("policyName"))
    policy_id = account.get("policyId")
    strategy = _clean(account.get("strategy"))
    correlation_method = _clean(account.get("correlationMethod"))
    attempts = account.get("correlationAttempts")
    attempts = attempts if isinstance(attempts, list) else []
    matched_identity = account.get("matchedIdentity")
    matched_identity = matched_identity if isinstance(matched_identity, dict) else None
    ambiguous_identities = _matched_identities(
        [attempt for attempt in attempts if isinstance(attempt, dict)]
    )

    heading_bits: list[str] = []
    if employee_id:
        heading_bits.append(f"employee ID {employee_id}")
    if username:
        heading_bits.append(f"account {username}")
    heading = f" ({', '.join(heading_bits)})" if heading_bits else ""

    lines = [
        f"**{label}**{heading} is currently classified as **{orphan_type}**.",
        f"- **Reason:** {reason}",
    ]
    if application:
        lines.append(f"- **Application:** {application}")
    if integration and integration != application:
        lines.append(f"- **Source:** {integration}")
    if orphan_status:
        lines.append(f"- **Orphan status:** {orphan_status}")

    if policy_name or policy_id is not None or strategy:
        policy_parts: list[str] = []
        if policy_name:
            policy_parts.append(policy_name)
        if policy_id is not None:
            policy_parts.append(f"ID {policy_id}")
        if strategy:
            policy_parts.append(f"strategy {strategy}")
        lines.append(f"- **Correlation policy:** {', '.join(policy_parts)}")

    if correlation_method:
        lines.append(f"- **Successful correlation method:** {correlation_method}")

    if attempts:
        lines.extend(["", "**Correlation attempts**"])
        for index, attempt in enumerate(attempts, start=1):
            if isinstance(attempt, dict):
                lines.append(_attempt_line(attempt, index))
    else:
        lines.extend(["", "No persisted correlation-attempt detail is available for this orphan state."])

    if matched_identity:
        lines.extend(["", "**Matched authoritative identity**"])
        identity_bits = [_identity_label(matched_identity)]
        if _clean(matched_identity.get("employeeId")):
            identity_bits.append(f"employee ID {matched_identity['employeeId']}")
        if _clean(matched_identity.get("employmentStatus")):
            identity_bits.append(f"status {matched_identity['employmentStatus']}")
        lines.append("- " + " — ".join(identity_bits))
    elif ambiguous_identities:
        lines.extend(["", "**Authoritative identities matched by the ambiguous rule**"])
        for identity in ambiguous_identities[:10]:
            identity_bits = [_identity_label(identity)]
            if _clean(identity.get("employeeId")):
                identity_bits.append(f"employee ID {identity['employeeId']}")
            if _clean(identity.get("employmentStatus")):
                identity_bits.append(f"status {identity['employmentStatus']}")
            lines.append("- " + " — ".join(identity_bits))
    elif orphan_type == "UNMATCHED_ACCOUNT":
        lines.extend(
            [
                "",
                "No authoritative identity was matched by the persisted correlation attempts.",
            ]
        )

    return "\n".join(lines)


class ExplainOrphanAccountTool(BaseAITool):
    name = "explain_orphan_account"
    description = (
        "Explain WHY one CURRENT orphan account is orphaned using persisted IdentityAI "
        "correlation evidence. Use for questions about the failed correlation rule, evaluated "
        "attributes, source values, match outcomes, ambiguity, correlation policy, or the "
        "authoritative identity that matched. Resolve the account by a human reference such as "
        "display name, username, email, employee ID, native identity, or by grounded "
        "source_account_id. Never invent a rule, identity, or correlation result."
    )
    parameters = {
        "type": "object",
        "properties": {
            "reference": {
                "type": ["string", "null"],
                "description": (
                    "Human account reference such as display name, username, email, employee ID, "
                    "native identity, or a natural-language phrase containing one of them."
                ),
            },
            "source_account_id": {
                "type": ["integer", "null"],
                "description": "Grounded persistent source-account ID when already known.",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        reference = _clean(arguments.get("reference"))
        source_account_id = arguments.get("source_account_id")
        if source_account_id is not None:
            try:
                source_account_id = int(source_account_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("source_account_id must be numeric.") from exc

        if source_account_id is None and not reference:
            return {
                "resultType": "orphan_explanation",
                "found": False,
                "requiresInput": True,
                "message": (
                    "Please identify the orphan account by display name, username, email, "
                    "employee ID, native identity, or select one from the current results."
                ),
            }

        items = list_orphan_accounts(
            db,
            source_account_id=source_account_id,
            search=reference if source_account_id is None else None,
            limit=10,
        )

        if not items:
            target = reference or str(source_account_id)
            return {
                "resultType": "orphan_explanation",
                "found": False,
                "message": f"No current orphan account matched **{target}**.",
            }

        if len(items) > 1:
            candidates = [
                {
                    "sourceAccountId": item.get("sourceAccountId"),
                    "displayName": item.get("displayName"),
                    "username": item.get("username"),
                    "employeeId": item.get("employeeId"),
                    "application": item.get("application"),
                    "integrationName": item.get("integrationName"),
                }
                for item in items
            ]
            candidate_lines = [
                "Multiple current orphan accounts matched that reference. Please choose one:"
            ]
            for candidate in candidates:
                label = _account_label(candidate)
                details = [
                    str(value)
                    for value in (
                        candidate.get("employeeId"),
                        candidate.get("username"),
                        candidate.get("application"),
                    )
                    if value not in (None, "")
                ]
                suffix = f" — {', '.join(details)}" if details else ""
                candidate_lines.append(f"- **{label}**{suffix}")
            return {
                "resultType": "orphan_explanation",
                "found": False,
                "requiresSelection": True,
                "candidates": candidates,
                "message": "\n".join(candidate_lines),
            }

        account = items[0]
        report_filters: dict[str, Any] = {}
        if account.get("integrationId") is not None:
            report_filters["integrationId"] = account.get("integrationId")
        grounded_search = (
            account.get("employeeId")
            or account.get("username")
            or account.get("nativeIdentity")
            or account.get("displayName")
        )
        if grounded_search:
            report_filters["search"] = grounded_search

        attempts = account.get("correlationAttempts")
        attempts = attempts if isinstance(attempts, list) else []
        explanation = {
            "reason": account.get("reason"),
            "orphanType": account.get("orphanType"),
            "orphanStatus": account.get("orphanStatus"),
            "policyId": account.get("policyId"),
            "policyName": account.get("policyName"),
            "strategy": account.get("strategy"),
            "correlationMethod": account.get("correlationMethod"),
            "correlationAttempts": attempts,
            "matchedIdentity": account.get("matchedIdentity"),
            "matchedIdentities": _matched_identities(
                [attempt for attempt in attempts if isinstance(attempt, dict)]
            ),
        }
        return {
            "resultType": "orphan_explanation",
            "found": True,
            "account": account,
            "explanation": explanation,
            "reportType": "orphan_accounts",
            "reportFilters": report_filters,
            "message": _format_explanation(account),
        }
