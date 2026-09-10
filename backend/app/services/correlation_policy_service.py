from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db_models.correlation_policy import CorrelationPolicyRecord, CorrelationRuleRecord
from app.db_models.integration import IntegrationRecord
from app.schemas.correlation_policy import CorrelationPolicyInput, CorrelationPolicyUpdate


def policy_to_dict(policy: CorrelationPolicyRecord) -> dict:
    return {
        "id": policy.id,
        "name": policy.name,
        "accountIntegrationId": policy.account_integration_id,
        "authoritativeIntegrationId": policy.authoritative_integration_id,
        "strategy": policy.strategy,
        "enabled": policy.enabled,
        "rules": [
            {
                "id": rule.id,
                "priority": rule.priority,
                "accountAttribute": rule.account_attribute,
                "identityAttribute": rule.identity_attribute,
                "matchType": rule.match_type,
                "enabled": rule.enabled,
            }
            for rule in sorted(policy.rules, key=lambda item: item.priority)
        ],
        "createdAt": policy.created_at.isoformat(),
        "updatedAt": policy.updated_at.isoformat(),
    }


def _validate_integrations(
    db: Session,
    *,
    account_integration_id: int,
    authoritative_integration_id: int,
) -> None:
    account_source = db.get(IntegrationRecord, account_integration_id)
    authoritative_source = db.get(IntegrationRecord, authoritative_integration_id)
    if account_source is None:
        raise ValueError("Account integration not found.")
    if authoritative_source is None:
        raise ValueError("Authoritative integration not found.")
    if account_source.source_purpose != "ACCOUNT":
        raise ValueError("accountIntegrationId must reference an ACCOUNT integration.")
    if authoritative_source.source_purpose != "AUTHORITATIVE":
        raise ValueError(
            "authoritativeIntegrationId must reference an AUTHORITATIVE integration."
        )


def _replace_rules(
    db: Session,
    policy: CorrelationPolicyRecord,
    rules,
) -> None:
    priorities = [rule.priority for rule in rules]
    if len(priorities) != len(set(priorities)):
        raise ValueError("Correlation rule priorities must be unique.")

    db.execute(delete(CorrelationRuleRecord).where(CorrelationRuleRecord.policy_id == policy.id))
    db.flush()
    for rule in sorted(rules, key=lambda item: item.priority):
        db.add(
            CorrelationRuleRecord(
                policy_id=policy.id,
                priority=rule.priority,
                account_attribute=rule.accountAttribute,
                identity_attribute=rule.identityAttribute,
                match_type=rule.matchType,
                enabled=rule.enabled,
            )
        )


def create_policy(db: Session, payload: CorrelationPolicyInput) -> CorrelationPolicyRecord:
    _validate_integrations(
        db,
        account_integration_id=payload.accountIntegrationId,
        authoritative_integration_id=payload.authoritativeIntegrationId,
    )
    policy = CorrelationPolicyRecord(
        name=payload.name.strip(),
        account_integration_id=payload.accountIntegrationId,
        authoritative_integration_id=payload.authoritativeIntegrationId,
        strategy=payload.strategy,
        enabled=payload.enabled,
    )
    db.add(policy)
    db.flush()
    _replace_rules(db, policy, payload.rules)
    db.commit()
    return get_policy(db, policy.id)


def get_policy(db: Session, policy_id: int) -> CorrelationPolicyRecord | None:
    return db.scalar(
        select(CorrelationPolicyRecord)
        .options(selectinload(CorrelationPolicyRecord.rules))
        .where(CorrelationPolicyRecord.id == policy_id)
    )


def get_policy_for_account_integration(
    db: Session,
    account_integration_id: int,
) -> CorrelationPolicyRecord | None:
    return db.scalar(
        select(CorrelationPolicyRecord)
        .options(selectinload(CorrelationPolicyRecord.rules))
        .where(
            CorrelationPolicyRecord.account_integration_id == account_integration_id,
            CorrelationPolicyRecord.enabled.is_(True),
        )
        .order_by(CorrelationPolicyRecord.id.desc())
    )


def list_policies(db: Session) -> list[CorrelationPolicyRecord]:
    return list(
        db.scalars(
            select(CorrelationPolicyRecord)
            .options(selectinload(CorrelationPolicyRecord.rules))
            .order_by(CorrelationPolicyRecord.name.asc(), CorrelationPolicyRecord.id.asc())
        ).all()
    )


def update_policy(
    db: Session,
    policy: CorrelationPolicyRecord,
    payload: CorrelationPolicyUpdate,
) -> CorrelationPolicyRecord:
    update_data = payload.model_dump(exclude_unset=True)
    authoritative_id = update_data.get(
        "authoritativeIntegrationId", policy.authoritative_integration_id
    )
    _validate_integrations(
        db,
        account_integration_id=policy.account_integration_id,
        authoritative_integration_id=authoritative_id,
    )
    if "name" in update_data:
        policy.name = str(update_data["name"]).strip()
    if "authoritativeIntegrationId" in update_data:
        policy.authoritative_integration_id = int(update_data["authoritativeIntegrationId"])
    if "strategy" in update_data:
        policy.strategy = str(update_data["strategy"])
    if "enabled" in update_data:
        policy.enabled = bool(update_data["enabled"])
    if payload.rules is not None:
        _replace_rules(db, policy, payload.rules)
    db.commit()
    return get_policy(db, policy.id)


def delete_policy(db: Session, policy: CorrelationPolicyRecord) -> None:
    db.delete(policy)
    db.commit()
