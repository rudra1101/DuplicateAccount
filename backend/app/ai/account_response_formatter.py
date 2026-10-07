from __future__ import annotations

from typing import Any


def _value(value: Any) -> str:
    return str(value or "").strip()


def _format_account(item: dict[str, Any]) -> str:
    lines: list[str] = []

    display_name = _value(item.get("displayName"))
    username = _value(item.get("username"))
    application = _value(item.get("application"))
    integration = _value(item.get("integrationName"))
    email = _value(item.get("email"))
    employee_id = _value(item.get("employeeId"))
    native_identity = _value(item.get("nativeIdentity"))
    account_status = _value(item.get("accountStatus"))

    heading = display_name or username or employee_id or native_identity or "Account"
    lines.append(f"**{heading}**")

    if application:
        lines.append(f"Application: {application}")
    elif integration:
        lines.append(f"Integration: {integration}")

    if username:
        lines.append(f"Username: {username}")
    if email:
        lines.append(f"Email: {email}")
    if employee_id:
        lines.append(f"Employee ID: {employee_id}")
    if native_identity:
        lines.append(f"Native Identity: {native_identity}")
    if account_status:
        lines.append(f"Status: {account_status}")

    orphaned = bool(item.get("orphaned"))
    lines.append(f"Orphaned: {'Yes' if orphaned else 'No'}")

    if orphaned:
        orphan_type = _value(item.get("orphanType"))
        orphan_status = _value(item.get("orphanStatus"))
        reason = _value(item.get("reason"))
        correlation_method = _value(item.get("correlationMethod"))
        policy_name = _value(item.get("policyName"))

        if orphan_type:
            lines.append(f"Orphan Type: {orphan_type}")
        if orphan_status:
            lines.append(f"Orphan Status: {orphan_status}")
        if reason:
            lines.append(f"Reason: {reason}")
        if correlation_method:
            lines.append(f"Correlation Method: {correlation_method}")
        if policy_name:
            lines.append(f"Correlation Policy: {policy_name}")

    return "\n".join(lines)


def format_account_investigation_result(data: dict[str, Any]) -> str:
    """Render account-investigation data without another LLM synthesis pass."""

    message = _value(data.get("message"))
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return message or "No matching active accounts were found."

    formatted = [
        _format_account(item)
        for item in items
        if isinstance(item, dict)
    ]

    if not formatted:
        return message or "No matching active accounts were found."

    if len(formatted) == 1:
        return formatted[0]

    return (
        f"Found **{len(formatted)}** matching active accounts.\n\n"
        + "\n\n---\n\n".join(formatted)
    )
