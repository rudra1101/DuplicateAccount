from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.authorization import get_rudrix_actor, has_rudrix_permission
from app.ai.tools.base import BaseAITool
from app.services.duplicate_group_feedback_service import save_duplicate_group_candidate_decision


class ReviewDuplicateCandidateTool(BaseAITool):
    name = "review_duplicate_candidate"
    description = (
        "Submit a review decision for a CURRENT duplicate candidate. Use this when the "
        "user asks to confirm/mark/approve the current candidate as a duplicate, mark "
        "it as not a duplicate, or mark it uncertain. The candidate must already be "
        "resolved from live duplicate data or grounded conversation state. Never invent an ID."
    )
    parameters = {
        "type": "object",
        "properties": {
            "candidate_id": {"type": ["integer", "null"], "minimum": 1},
            "decision": {
                "type": "string",
                "enum": ["DUPLICATE", "NOT_DUPLICATE", "UNCERTAIN"],
            },
            "comment": {"type": ["string", "null"]},
        },
        "required": ["candidate_id", "decision"],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        if not has_rudrix_permission("duplicate.review"):
            raise PermissionError(
                "You do not have permission to submit duplicate review decisions. "
                "The required permission is duplicate.review."
            )

        candidate_id = arguments.get("candidate_id")
        if candidate_id is None:
            raise ValueError("candidate_id is required for a duplicate review decision.")

        decision = str(arguments.get("decision") or "").strip().upper()
        if decision not in {"DUPLICATE", "NOT_DUPLICATE", "UNCERTAIN"}:
            raise ValueError("A valid duplicate review decision is required.")

        actor = get_rudrix_actor()
        user_comment = str(arguments.get("comment") or "").strip()
        audit_comment = "Submitted via Rudrix."
        if user_comment:
            audit_comment += f" {user_comment}"

        result = save_duplicate_group_candidate_decision(
            db=db,
            candidate_id=int(candidate_id),
            decision=decision,
            comment=audit_comment,
            reviewer_name=actor,
        )

        return {
            "message": f"Marked candidate **{int(candidate_id)}** as **{decision}**.",
            "candidateId": int(candidate_id),
            "decision": decision,
            "reviewer": actor,
            "result": result,
        }
