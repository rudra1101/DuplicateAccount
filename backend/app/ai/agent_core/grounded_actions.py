from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.ai.agent_core.models import AgentEntity, AgentState


@dataclass(frozen=True)
class GroundedAction:
    tool_name: str
    arguments: dict[str, object]


def _normalized(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split()).rstrip(".!?")


def _candidate_reference(candidate: AgentEntity | None) -> str | None:
    if candidate is None:
        return None

    attributes = candidate.attributes or {}
    account = attributes.get("account")
    if not isinstance(account, dict):
        account = {}

    values: tuple[Any, ...] = (
        attributes.get("username"),
        account.get("username"),
        account.get("employeeId"),
        account.get("employee_id"),
        account.get("email"),
        candidate.label,
    )
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _remediation_target(text: str) -> str | None:
    if re.search(r"\b(?:second|2nd|account\s*2|account_2)\b", text):
        return "ACCOUNT_2"
    if re.search(r"\b(?:first|1st|account\s*1|account_1)\b", text):
        return "ACCOUNT_1"
    return None


def _remediation_action(text: str) -> str | None:
    if re.search(r"\bdelete\b", text):
        return "DELETE"
    if re.search(r"\bdisable\b", text):
        return "DISABLE"
    return None


def _resolve_pending_remediation(text: str, state: AgentState) -> GroundedAction | None:
    pending = state.pending_action
    if pending is None or pending.capability != "create_remediation_ticket":
        return None

    arguments: dict[str, object] = dict(pending.arguments)
    target = _remediation_target(text)
    action = _remediation_action(text)
    if target:
        arguments["target"] = target
    if action:
        arguments["action"] = action

    create_confirmation = text in {
        "create it",
        "create the ticket",
        "create ticket",
        "raise it",
        "raise the ticket",
        "open it",
        "open the ticket",
        "proceed",
        "go ahead",
    }

    if arguments.get("remediation_item_id") and arguments.get("target") and arguments.get("action"):
        if target or action or create_confirmation:
            return GroundedAction(
                tool_name="create_remediation_ticket",
                arguments={
                    "remediation_item_id": arguments["remediation_item_id"],
                    "account_reference": None,
                    "target": arguments["target"],
                    "action": arguments["action"],
                },
            )

    return None


def _resolve_remediation_start(text: str, state: AgentState) -> GroundedAction | None:
    ticket_intent = bool(
        re.search(
            r"\b(?:create|raise|open|make)\b.*\b(?:ticket|incident)\b",
            text,
        )
    )
    if not ticket_intent:
        return None

    candidate_reference = _candidate_reference(state.current_duplicate_candidate)
    if not candidate_reference:
        return None

    return GroundedAction(
        tool_name="create_remediation_ticket",
        arguments={
            "remediation_item_id": None,
            "account_reference": candidate_reference,
            "target": _remediation_target(text),
            "action": _remediation_action(text),
        },
    )


def _resolve_duplicate_review(text: str, state: AgentState) -> GroundedAction | None:
    candidate = state.current_duplicate_candidate
    if candidate is None or candidate.id is None:
        return None

    not_duplicate = (
        "not duplicate" in text
        or "not a duplicate" in text
        or "false positive" in text
        or bool(re.search(r"\breject(?: it)?\b", text))
    )
    uncertain = bool(re.search(r"\b(?:uncertain|unsure|not sure|needs review)\b", text))
    duplicate = (
        text in {"confirm", "confirm it", "confirmed", "approve", "approve it", "yes confirm"}
        or bool(re.search(r"\b(?:confirm|approve|mark)\b.*\bduplicate\b", text))
    )

    if not_duplicate:
        decision = "NOT_DUPLICATE"
    elif uncertain:
        decision = "UNCERTAIN"
    elif duplicate:
        decision = "DUPLICATE"
    else:
        return None

    return GroundedAction(
        tool_name="review_duplicate_candidate",
        arguments={
            "candidate_id": int(candidate.id),
            "decision": decision,
            "comment": None,
        },
    )


def resolve_grounded_action(message: str, state: AgentState) -> GroundedAction | None:
    """Resolve an unambiguous write action from grounded conversation state.

    Open-ended requests still go through the agent planner. Explicit decisions about a
    uniquely grounded entity are executed without another model round trip. This also
    carries multi-turn remediation intent through structured pending action state so
    users never need to know internal remediation IDs.
    """

    text = _normalized(message)
    if not text:
        return None

    pending_remediation = _resolve_pending_remediation(text, state)
    if pending_remediation is not None:
        return pending_remediation

    remediation_start = _resolve_remediation_start(text, state)
    if remediation_start is not None:
        return remediation_start

    return _resolve_duplicate_review(text, state)
