from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.agent_core.models import AgentState


@dataclass(frozen=True)
class GroundedAction:
    tool_name: str
    arguments: dict[str, object]


def _normalized(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split()).rstrip(".!?")


def resolve_grounded_action(message: str, state: AgentState) -> GroundedAction | None:
    """Resolve an unambiguous write action from grounded conversation state.

    Open-ended requests still go through the agent planner. Explicit decisions about a
    uniquely grounded entity are executed without another model round trip.
    """

    candidate = state.current_duplicate_candidate
    if candidate is None or candidate.id is None:
        return None

    text = _normalized(message)
    if not text:
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
