from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.agent_core.models import AgentEntity, EntityType
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.source_account import SourceAccountRecord


def _entity(
    entity_type: EntityType,
    id_value: Any,
    label: Any,
    attributes: dict[str, Any],
) -> AgentEntity:
    return AgentEntity(
        entity_type=entity_type,
        id=id_value,
        label=str(label) if label not in (None, "") else None,
        attributes=attributes,
        source="entity_resolver",
    )


class DomainEntityResolver:
    """Resolve user-facing IdentityAI references to grounded product entities.

    The resolver is deliberately domain/data based. It does not interpret full
    user intent and does not rely on prompt phrases; the planner can ask it to
    resolve a reference before selecting downstream capabilities.
    """

    def __init__(self, db: Session):
        self.db = db

    def resolve_account(self, reference: str, limit: int = 10) -> list[AgentEntity]:
        value = " ".join(str(reference or "").strip().split())
        if not value:
            return []

        needle = f"%{value}%"
        statement = (
            select(SourceAccountRecord)
            .where(
                SourceAccountRecord.active.is_(True),
                or_(
                    SourceAccountRecord.native_identity.ilike(needle),
                    SourceAccountRecord.username.ilike(needle),
                    SourceAccountRecord.email.ilike(needle),
                    SourceAccountRecord.employee_id.ilike(needle),
                    SourceAccountRecord.display_name.ilike(needle),
                ),
            )
            .order_by(SourceAccountRecord.id.asc())
            .limit(max(1, min(limit, 20)))
        )
        rows = list(self.db.scalars(statement).all())
        return [
            _entity(
                EntityType.SOURCE_ACCOUNT,
                row.id,
                row.display_name or row.username or row.native_identity,
                {
                    "integrationId": row.integration_id,
                    "application": row.application,
                    "nativeIdentity": row.native_identity,
                    "username": row.username,
                    "displayName": row.display_name,
                    "email": row.email,
                    "employeeId": row.employee_id,
                    "status": row.status,
                },
            )
            for row in rows
        ]

    def resolve_integration(self, reference: str, limit: int = 10) -> list[AgentEntity]:
        value = " ".join(str(reference or "").strip().split())
        if not value:
            return []
        needle = f"%{value}%"
        rows = list(
            self.db.scalars(
                select(IntegrationRecord)
                .where(IntegrationRecord.name.ilike(needle))
                .order_by(IntegrationRecord.name.asc())
                .limit(max(1, min(limit, 20)))
            ).all()
        )
        return [
            _entity(
                EntityType.INTEGRATION,
                row.id,
                row.name,
                {"name": row.name},
            )
            for row in rows
        ]

    def resolve_duplicate_group(self, reference: str) -> list[AgentEntity]:
        value = str(reference or "").strip()
        if not value:
            return []

        conditions = [DuplicateGroupRecord.primary_username.ilike(f"%{value}%")]
        if value.isdigit():
            conditions.append(DuplicateGroupRecord.id == int(value))

        rows = list(
            self.db.scalars(
                select(DuplicateGroupRecord)
                .where(or_(*conditions))
                .order_by(DuplicateGroupRecord.id.desc())
                .limit(20)
            ).all()
        )
        return [
            _entity(
                EntityType.DUPLICATE_GROUP,
                row.id,
                row.primary_username,
                {
                    "application": row.application,
                    "primaryUsername": row.primary_username,
                    "duplicateCount": row.duplicate_count,
                    "highestConfidence": row.highest_confidence,
                },
            )
            for row in rows
        ]

    def resolve_duplicate_candidate(self, reference: str) -> list[AgentEntity]:
        value = str(reference or "").strip()
        if not value:
            return []

        conditions = [DuplicateCandidateRecord.username.ilike(f"%{value}%")]
        if value.isdigit():
            conditions.append(DuplicateCandidateRecord.id == int(value))

        rows = list(
            self.db.scalars(
                select(DuplicateCandidateRecord)
                .where(or_(*conditions))
                .order_by(DuplicateCandidateRecord.id.desc())
                .limit(20)
            ).all()
        )
        return [
            _entity(
                EntityType.DUPLICATE_CANDIDATE,
                row.id,
                row.username,
                {
                    "groupId": row.group_id,
                    "username": row.username,
                    "confidence": row.confidence,
                    "recommendation": row.recommendation,
                    "reviewDecision": row.review_decision,
                },
            )
            for row in rows
        ]

    def resolve(self, reference: str, expected_type: EntityType | None = None) -> list[AgentEntity]:
        if expected_type == EntityType.SOURCE_ACCOUNT:
            return self.resolve_account(reference)
        if expected_type == EntityType.INTEGRATION:
            return self.resolve_integration(reference)
        if expected_type == EntityType.DUPLICATE_GROUP:
            return self.resolve_duplicate_group(reference)
        if expected_type == EntityType.DUPLICATE_CANDIDATE:
            return self.resolve_duplicate_candidate(reference)

        # Account references are the most common human-facing identifiers in
        # IdentityAI, so resolve them first. Other entity types follow only when
        # there is no account match, avoiding unnecessary broad DB work.
        accounts = self.resolve_account(reference)
        if accounts:
            return accounts
        integrations = self.resolve_integration(reference)
        if integrations:
            return integrations
        groups = self.resolve_duplicate_group(reference)
        if groups:
            return groups
        return self.resolve_duplicate_candidate(reference)
