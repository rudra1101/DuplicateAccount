from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.db_models.identity import IdentityRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.source_account import SourceAccountRecord


class InvestigateAccountsTool(BaseAITool):
    name = "investigate_accounts"

    description = (
        "Search CURRENT source-account inventory across integrations and explain "
        "account correlation/orphan state using persisted IdentityAI evidence. "
        "Use this when the user asks to find/search/locate an account, asks whether "
        "an account is orphaned, asks why an account is orphaned or failed correlation, "
        "or asks which correlation attributes/rules were attempted. The result is "
        "read-only and includes the real correlation evidence recorded by the orphan engine."
    )

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Username, email, employee ID, native identity, or display-name text."
                ),
            },
            "application": {
                "type": ["string", "null"],
                "description": "Optional application name, for example Active Directory.",
            },
            "integration": {
                "type": ["string", "null"],
                "description": "Optional integration/source name used to narrow the search.",
            },
            "orphan_only": {
                "type": "boolean",
                "description": "Return only accounts currently flagged as active orphans.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["query", "application", "integration", "orphan_only", "limit"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("Account search text is required.")

        application = str(arguments.get("application") or "").strip()
        integration = str(arguments.get("integration") or "").strip()
        orphan_only = bool(arguments.get("orphan_only", False))
        limit = max(1, min(int(arguments.get("limit") or 10), 20))

        statement = select(SourceAccountRecord).where(
            SourceAccountRecord.active.is_(True),
            SourceAccountRecord.deleted.is_(False),
        )

        needle = f"%{query}%"
        statement = statement.where(
            or_(
                SourceAccountRecord.native_identity.ilike(needle),
                SourceAccountRecord.username.ilike(needle),
                SourceAccountRecord.email.ilike(needle),
                SourceAccountRecord.employee_id.ilike(needle),
                SourceAccountRecord.display_name.ilike(needle),
            )
        )

        if application:
            statement = statement.where(
                SourceAccountRecord.application.ilike(f"%{application}%")
            )

        if integration:
            integration_ids = list(
                db.scalars(
                    select(IntegrationRecord.id).where(
                        IntegrationRecord.name.ilike(f"%{integration}%")
                    )
                ).all()
            )
            if not integration_ids:
                return {
                    "query": query,
                    "count": 0,
                    "items": [],
                    "message": f"No integration matched '{integration}'.",
                }
            statement = statement.where(
                SourceAccountRecord.integration_id.in_(integration_ids)
            )

        if orphan_only:
            statement = statement.join(
                OrphanStateRecord,
                OrphanStateRecord.source_account_id == SourceAccountRecord.id,
            ).where(
                OrphanStateRecord.active.is_(True),
                OrphanStateRecord.status == "OPEN",
            )

        rows = list(
            db.scalars(
                statement
                .order_by(
                    SourceAccountRecord.application.asc(),
                    SourceAccountRecord.native_identity.asc(),
                )
                .limit(limit)
            ).all()
        )

        if not rows:
            return {
                "query": query,
                "count": 0,
                "items": [],
                "message": "No matching active accounts were found.",
            }

        source_account_ids = [row.id for row in rows]
        integration_ids = sorted({row.integration_id for row in rows})

        states = list(
            db.scalars(
                select(OrphanStateRecord).where(
                    OrphanStateRecord.source_account_id.in_(source_account_ids),
                    OrphanStateRecord.active.is_(True),
                )
            ).all()
        )
        state_by_account = {state.source_account_id: state for state in states}

        integrations = list(
            db.scalars(
                select(IntegrationRecord).where(
                    IntegrationRecord.id.in_(integration_ids)
                )
            ).all()
        )
        integration_by_id = {item.id: item for item in integrations}

        identity_ids = sorted(
            {
                state.matched_identity_id
                for state in states
                if state.matched_identity_id is not None
            }
        )
        identities = (
            list(
                db.scalars(
                    select(IdentityRecord).where(IdentityRecord.id.in_(identity_ids))
                ).all()
            )
            if identity_ids
            else []
        )
        identity_by_id = {identity.id: identity for identity in identities}

        items: list[dict[str, Any]] = []
        for account in rows:
            state = state_by_account.get(account.id)
            integration_record = integration_by_id.get(account.integration_id)
            evidence = dict(state.evidence or {}) if state is not None else {}
            matched_identity = (
                identity_by_id.get(state.matched_identity_id)
                if state is not None and state.matched_identity_id is not None
                else None
            )

            identity_summary = None
            if matched_identity is not None:
                identity_summary = {
                    "id": matched_identity.id,
                    "sourceIdentityId": matched_identity.source_identity_id,
                    "displayName": matched_identity.display_name,
                    "username": matched_identity.username,
                    "email": matched_identity.email,
                    "employeeId": matched_identity.employee_id,
                    "employmentStatus": matched_identity.employment_status,
                }

            items.append(
                {
                    "sourceAccountId": account.id,
                    "integrationId": account.integration_id,
                    "integrationName": (
                        integration_record.name if integration_record is not None else None
                    ),
                    "application": account.application,
                    "nativeIdentity": account.native_identity,
                    "username": account.username,
                    "displayName": account.display_name,
                    "email": account.email,
                    "employeeId": account.employee_id,
                    "accountStatus": account.status,
                    "orphaned": state is not None,
                    "orphanType": state.orphan_type if state is not None else None,
                    "orphanStatus": state.status if state is not None else None,
                    "correlationMethod": (
                        state.correlation_method if state is not None else None
                    ),
                    "reason": evidence.get("reason"),
                    "policyId": evidence.get("policyId"),
                    "policyName": evidence.get("policyName"),
                    "strategy": evidence.get("strategy"),
                    "correlationAttempts": evidence.get("correlationAttempts") or [],
                    "matchedIdentity": identity_summary,
                    "lastSeenAt": (
                        account.last_seen_at.isoformat() if account.last_seen_at else None
                    ),
                }
            )

        return {
            "query": query,
            "count": len(items),
            "items": items,
            "statusMeaning": {
                "orphanedTrue": "Account is currently flagged by the orphan engine.",
                "orphanedFalse": (
                    "Account is not currently flagged as an orphan; this does not by "
                    "itself prove a human identity correlation."
                ),
            },
        }
