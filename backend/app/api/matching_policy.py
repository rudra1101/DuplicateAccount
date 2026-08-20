from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import require_any_permission
from app.schemas.application_schema import SchemaAttributeInput
from app.services.matching_policy_service import generate_matching_policy


router = APIRouter(
    prefix="/matching-policy",
    tags=["Matching Policy"],
)


class MatchingPolicyRequest(BaseModel):
    applicationName: str = Field(min_length=1, max_length=255)
    attributes: list[SchemaAttributeInput] = Field(min_length=1)


@router.post("/generate")
def generate_policy(
    payload: MatchingPolicyRequest,
    _user=Depends(
        require_any_permission(
            "integration.create",
            "integration.edit",
        )
    ),
):
    attributes = [
        attribute.model_dump()
        for attribute in payload.attributes
    ]

    result = generate_matching_policy(attributes)
    result["applicationName"] = payload.applicationName.strip()
    return result
