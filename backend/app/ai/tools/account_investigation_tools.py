from __future__ import annotations

import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.db_models.identity import IdentityRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.source_account import SourceAccountRecord


_NULLISH_FILTER_VALUES = {
    "",
    "null",
    "none",
    "n/a",
    "na",
    "any",
    "all",
    "not specified",
    "unspecified",
    "no application",
    "null application",
    "no integration",
    "null integration",
}

_ACCOUNT_QUERY_PREFIXES = (
    r"^\s*(?:find|locate|lookup|look\s+up)\s+(?:the\s+)?(?:account|accout)?\s*(?:for\s+)?",
    r"^\s*search\s+(?:for\s+)?(?:the\s+)?(?:account|accout)?\s*(?:for\s+)?",
    r"^\s*(?:account|accout)\s+(?:for\s+)?",
)


def _optional_filter(value: Any) -> str:
    """Normalize optional model-supplied filters.

    Local models sometimes serialize an omitted nullable argument as strings
    such as ``null`` or ``null application``. Treat those values exactly like
    an omitted filter so broad account searches are not accidentally narrowed
    to a non-existent source.
    """
    text = str(value or "").strip()
    if text.casefold() in _NULLISH_FILTER_VALUES:
        return ""
    return text


def _normalize_account_query(value: Any) -> str:
    """Reduce a model-supplied natural-language search phrase to search text.

    Local models sometimes pass the entire user sentence as the tool's ``query``
    argument (for example ``find account for Aditya Sinha``). Source account
    inventory stores only the actual account attributes, so searching for the
    complete sentence can never match. Strip only known leading lookup phrases
    and leave real usernames, emails, employee IDs, and display names unchanged.
    """
    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""

    for pattern in _ACCOUNT_QUERY_PREFIXES:
        normalized = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if normalized != text:
            text = normalized
            break

    # Models occasionally wrap the extracted value in quotes or append simple
    # punctuation from the user sentence. These characters are not meaningful
    # for account lookup and can prevent an otherwise exact display-name match.
    return text.strip(" \t\r\n\"'?.!,;:")


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
                    "Username, email, employee ID, native identity, or display-name text. "
                    "Pass only the account value/name, not the full user sentence."
                ),
            },
            "application": {
                "type": "string",
                "description": (
                    "Optional application name, for example Active Directory. "
                    "Omit this field when the user did not specify an application."
                ),
            },
            "integration": {
                "type": "string",
                "description": (
                    "Optional integration/source name used to narrow the search. "
                    "Omit this field when the user did not specify an integration."
                ),
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        raw_query = str(arguments.get("query") or "").strip()
        query = _normalize_account_query(raw_query)
        if not query:
            raise ValueError("Account search text is required.")

        application = _optional_filter(arguments.get("application"))
        integration = _optional_filter(arguments.get("integration"))
        limit = max(1, min(int(arguments.get("limit") or 10), 20))

        # Match the Account Inventory page semantics: current inventory is
        # defined by active=True. Do not add a second deleted=False constraint,
        # because legacy rows can have inconsistent flags and still appear in
        # the UI inventory. Investigation must search the same visible dataset.
        statement = select(SourceAccountRecord).where(
            SourceAccountRecord.active.is_(True),
        )

        needle = f"%{query}%"
        statement = statement.where(
            or_(
                SourceAccountRecord.native_identity.ilike(needle),
                SourceAccountRecord.username.ilike(needle),
                SourceAccountRecord.email.ilike(needle),
                SourceAccountRecord.employee_id.ilike(needle),
                SourceAccountRecord.display_name.ilike(needle),
                SourceAccountRecord.application.ilike(needle),
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
                    "originalQuery": raw_query if raw_query != query else None,
                    "count": 0,
                    "items": [],
                    "message": f"No integration matched '{integration}'.",
                }
            statement = statement.where(
                SourceAccountRecord.integration_id.in_(integration_ids)
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
                "originalQuery": raw_query if raw_query != query else None,
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
            "originalQuery": raw_query if raw_query != query else None,
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
