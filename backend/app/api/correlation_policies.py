from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.schemas.correlation_policy import CorrelationPolicyInput, CorrelationPolicyUpdate
from app.services.correlation_policy_service import (
    create_policy,
    delete_policy,
    get_policy,
    list_policies,
    policy_to_dict,
    update_policy,
)


router = APIRouter(prefix="/correlation-policies", tags=["Correlation Policies"])


@router.get("/")
def get_all(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    return [policy_to_dict(policy) for policy in list_policies(db)]


@router.get("/{policy_id}")
def get_one(
    policy_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.view")),
):
    policy = get_policy(db, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Correlation policy not found.")
    return policy_to_dict(policy)


@router.post("/")
def create(
    payload: CorrelationPolicyInput,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.edit")),
):
    try:
        return policy_to_dict(create_policy(db, payload))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Correlation policy already exists.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{policy_id}")
def update(
    policy_id: int,
    payload: CorrelationPolicyUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.edit")),
):
    policy = get_policy(db, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Correlation policy not found.")
    try:
        return policy_to_dict(update_policy(db, policy, payload))
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Correlation policy conflicts with an existing policy.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{policy_id}", status_code=204)
def delete(
    policy_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("integration.edit")),
):
    policy = get_policy(db, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Correlation policy not found.")
    delete_policy(db, policy)
