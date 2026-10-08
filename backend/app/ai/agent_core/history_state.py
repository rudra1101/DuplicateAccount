from __future__ import annotations

import re
from typing import Any

from app.ai.agent_core.models import AgentEntity, AgentState, EntityType


def _history_content(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return str(getattr(message, "content", "") or "")


def _history_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role") or "")
    return str(getattr(message, "role", "") or "")


def _field(text: str, label: str) -> str | None:
    match = re.search(
        rf"(?:^|\n)\s*(?:[-*]\s*)?{re.escape(label)}\s*:\s*([^\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).strip().strip("`* ")
    return value or None


def hydrate_state_from_history(history: list[Any]) -> AgentState:
    """Recover grounded entity context from deterministic Rudrix responses.

    This is intentionally conservative. It only parses labels emitted by our
    deterministic response formatters and never treats arbitrary user prose as
    authoritative state. Persistent conversation-state storage can replace this
    compatibility layer later without changing planner contracts.
    """

    state = AgentState()
    assistant_messages = [
        _history_content(message)
        for message in history
        if _history_role(message).lower() == "assistant"
    ]

    for text in assistant_messages[-8:]:
        employee_id = _field(text, "Employee ID")
        username = _field(text, "Username")
        application = _field(text, "Application")
        native_identity = _field(text, "Native Identity")
        if employee_id or username or native_identity:
            state.current_account = AgentEntity(
                entity_type=EntityType.SOURCE_ACCOUNT,
                id=None,
                label=username or employee_id or native_identity,
                attributes={
                    key: value
                    for key, value in {
                        "employeeId": employee_id,
                        "username": username,
                        "application": application,
                        "nativeIdentity": native_identity,
                    }.items()
                    if value is not None
                },
                source="conversation_history",
            )

        group_id = _field(text, "Duplicate Group ID")
        primary = _field(text, "Primary account") or _field(text, "Primary Account")
        confidence = _field(text, "Highest Confidence")
        if group_id:
            parsed_group_id: int | str = int(group_id) if group_id.isdigit() else group_id
            state.current_duplicate_group = AgentEntity(
                entity_type=EntityType.DUPLICATE_GROUP,
                id=parsed_group_id,
                label=primary,
                attributes={
                    key: value
                    for key, value in {
                        "primaryUsername": primary,
                        "highestConfidence": confidence,
                        "application": application,
                    }.items()
                    if value is not None
                },
                source="conversation_history",
            )

        candidate_matches = list(
            re.finditer(
                r"\*\*([^*\n]+)\*\*\s*[—-]\s*candidate\s+ID\s+(\d+)\s*,\s*([0-9.]+)%\s+confidence",
                text,
                flags=re.IGNORECASE,
            )
        )
        if len(candidate_matches) == 1:
            match = candidate_matches[0]
            candidate_id = int(match.group(2))
            state.current_duplicate_candidate = AgentEntity(
                entity_type=EntityType.DUPLICATE_CANDIDATE,
                id=candidate_id,
                label=match.group(1).strip(),
                attributes={
                    "username": match.group(1).strip(),
                    "confidence": float(match.group(3)),
                    "groupId": (
                        state.current_duplicate_group.id
                        if state.current_duplicate_group is not None
                        else None
                    ),
                },
                source="conversation_history",
            )

        remediation_id = _field(text, "Remediation Item ID") or _field(text, "Remediation item")
        if remediation_id and remediation_id.isdigit():
            state.current_remediation_item = AgentEntity(
                entity_type=EntityType.REMEDIATION_ITEM,
                id=int(remediation_id),
                label=None,
                attributes={},
                source="conversation_history",
            )

    return state
