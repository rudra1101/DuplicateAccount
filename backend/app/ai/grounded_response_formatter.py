from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _format_account(item: dict[str, Any]) -> str:
    display_name = _text(item.get("displayName"))
    username = _text(item.get("username"))
    employee_id = _text(item.get("employeeId"))
    native_identity = _text(item.get("nativeIdentity"))
    heading = display_name or username or employee_id or native_identity or "Account"

    lines = [f"**{heading}**"]
    fields = (
        ("Application", item.get("application")),
        ("Username", username),
        ("Email", item.get("email")),
        ("Employee ID", employee_id),
        ("Native Identity", native_identity),
        ("Status", item.get("accountStatus")),
    )
    for label, value in fields:
        text = _text(value)
        if text and text.lower() != "null":
            lines.append(f"{label}: {text}")

    orphaned = bool(item.get("orphaned"))
    lines.append(f"Orphaned: {'Yes' if orphaned else 'No'}")
    if orphaned:
        for label, key in (
            ("Orphan Type", "orphanType"),
            ("Orphan Status", "orphanStatus"),
            ("Reason", "reason"),
            ("Correlation Method", "correlationMethod"),
            ("Correlation Policy", "policyName"),
        ):
            value = _text(item.get(key))
            if value and value.lower() != "null":
                lines.append(f"{label}: {value}")

    return "\n".join(lines)


def format_account_investigation(data: dict[str, Any]) -> str:
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return _text(data.get("message")) or "No matching active accounts were found."

    blocks = [_format_account(item) for item in items if isinstance(item, dict)]
    if not blocks:
        return _text(data.get("message")) or "No matching active accounts were found."
    if len(blocks) == 1:
        return blocks[0]
    return f"Found **{len(blocks)}** matching active accounts.\n\n" + "\n\n---\n\n".join(blocks)


def _format_candidate(candidate: dict[str, Any]) -> str:
    username = _text(candidate.get("username")) or "Unknown username"
    candidate_id = candidate.get("id")
    confidence = candidate.get("confidence")
    review_decision = _text(candidate.get("reviewDecision"))

    line = f"- **{username}**"
    details: list[str] = []
    if candidate_id is not None:
        details.append(f"candidate ID {candidate_id}")
    if confidence is not None:
        try:
            details.append(f"{float(confidence):g}% confidence")
        except (TypeError, ValueError):
            pass
    if review_decision:
        details.append(f"review: {review_decision}")
    if details:
        line += " — " + ", ".join(details)
    return line


def format_duplicate_search(data: dict[str, Any]) -> str:
    groups = data.get("groups")
    total = int(data.get("totalMatchingGroups") or 0)
    if not isinstance(groups, list) or total <= 0:
        return "No current duplicate group matched that account."

    blocks: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        primary = group.get("primaryAccount") or {}
        primary_username = _text(primary.get("username")) or _text(group.get("primaryUsername"))
        display_name = _text(primary.get("displayName"))
        employee_id = _text(primary.get("employeeId"))
        application = _text(group.get("application"))
        confidence = group.get("highestConfidence")
        group_id = group.get("groupId")

        heading = display_name or primary_username or employee_id or "Duplicate group"
        lines = [f"**{heading} has current duplicate candidate(s).**"]
        if application:
            lines.append(f"Application: {application}")
        if primary_username:
            lines.append(f"Primary account: {primary_username}")
        if employee_id:
            lines.append(f"Employee ID: {employee_id}")
        if group_id is not None:
            lines.append(f"Duplicate Group ID: {group_id}")
        if confidence is not None:
            try:
                lines.append(f"Highest Confidence: {float(confidence):g}%")
            except (TypeError, ValueError):
                pass

        candidates = group.get("candidates") or []
        if candidates:
            lines.append("Candidates:")
            lines.extend(_format_candidate(item) for item in candidates if isinstance(item, dict))
        blocks.append("\n".join(lines))

    if not blocks:
        return "No current duplicate group matched that account."
    if len(blocks) == 1:
        return blocks[0]
    return f"Found **{total}** current duplicate groups.\n\n" + "\n\n---\n\n".join(blocks)


def grounded_tool_message(
    tool_name: str,
    result: Any,
) -> str | None:
    if not isinstance(result, dict) or not result.get("success"):
        return None
    data = result.get("data")
    if not isinstance(data, dict):
        return None

    if tool_name == "investigate_accounts":
        return format_account_investigation(data)
    if tool_name == "search_duplicate_groups":
        return format_duplicate_search(data)
    return None
