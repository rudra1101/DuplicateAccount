from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.db_models.scan import ScanRecord
from app.services.integration_service import integration_to_dict


def _find_integration(
    db: Session,
    value: Any,
) -> IntegrationRecord | None:
    text = str(value or "").strip()
    if not text:
        return None

    if text.isdigit():
        return db.get(IntegrationRecord, int(text))

    normalized = text.lower()

    aliases = {
        "ad": "active directory",
        "azure ad": "entra",
        "azure active directory": "entra",
        "snow": "servicenow",
        "service now": "servicenow",
        "adp": "adp",
    }
    normalized = aliases.get(normalized, normalized)

    return db.scalars(
        select(IntegrationRecord)
        .where(
            or_(
                func.lower(IntegrationRecord.name)
                == normalized,
                func.lower(IntegrationRecord.name)
                .like(f"%{normalized}%"),
                func.lower(IntegrationRecord.connector_type)
                .like(f"%{normalized}%"),
            )
        )
        .order_by(IntegrationRecord.name.asc())
        .limit(1)
    ).first()


class ListIntegrationsTool(BaseAITool):
    name = "list_integrations"

    description = (
        "List configured account-source integrations, including "
        "connector type and enabled status."
    )

    parameters = {
        "type": "object",
        "properties": {
            "enabled_only": {"type": "boolean"},
        },
        "required": ["enabled_only"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        statement = select(IntegrationRecord).order_by(
            IntegrationRecord.name.asc()
        )

        if arguments.get("enabled_only", False):
            statement = statement.where(
                IntegrationRecord.enabled.is_(True)
            )

        integrations = db.scalars(statement).all()

        return {
            "count": len(integrations),
            "integrations": [
                integration_to_dict(integration)
                for integration in integrations
            ],
        }


class GetIntegrationDetailsTool(BaseAITool):
    name = "get_integration_details"

    description = (
        "Get one integration's configuration summary, enabled status, "
        "latest scan, and latest execution. The integration may be "
        "identified by name, connector type, alias, or numeric ID."
    )

    parameters = {
        "type": "object",
        "properties": {
            "integration": {
                "type": "string",
                "minLength": 1,
            },
        },
        "required": ["integration"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        integration = _find_integration(
            db,
            arguments["integration"],
        )

        if integration is None:
            return {
                "found": False,
                "message": "Integration was not found.",
            }

        latest_scan = db.scalars(
            select(ScanRecord)
            .where(
                ScanRecord.integration_id
                == integration.id
            )
            .order_by(
                ScanRecord.created_at.desc(),
                ScanRecord.id.desc(),
            )
            .limit(1)
        ).first()

        latest_execution = db.scalars(
            select(JobExecutionRecord)
            .where(
                JobExecutionRecord.integration_id
                == integration.id
            )
            .order_by(
                JobExecutionRecord.started_at.desc(),
                JobExecutionRecord.id.desc(),
            )
            .limit(1)
        ).first()

        return {
            "found": True,
            "integration": integration_to_dict(integration),
            "latestScan": (
                {
                    "id": latest_scan.id,
                    "filename": latest_scan.filename,
                    "status": latest_scan.status,
                    "accountsScanned": latest_scan.accounts_scanned,
                    "applications": latest_scan.application_count,
                    "duplicateGroups": (
                        latest_scan.duplicate_group_count
                    ),
                    "duplicateAccounts": (
                        latest_scan.duplicate_account_count
                    ),
                    "highConfidenceMatches": (
                        latest_scan.high_confidence_count
                    ),
                    "createdAt": (
                        latest_scan.created_at.isoformat()
                        if latest_scan.created_at
                        else None
                    ),
                }
                if latest_scan
                else None
            ),
            "latestExecution": (
                {
                    "id": latest_execution.id,
                    "scanId": latest_execution.scan_id,
                    "status": latest_execution.status,
                    "sourceFileName": (
                        latest_execution.source_file_name
                    ),
                    "accountsScanned": (
                        latest_execution.accounts_scanned
                    ),
                    "duplicateGroups": (
                        latest_execution.duplicate_groups
                    ),
                    "duplicateAccounts": (
                        latest_execution.duplicate_accounts
                    ),
                    "errorMessage": (
                        latest_execution.error_message
                    ),
                    "startedAt": (
                        latest_execution.started_at.isoformat()
                        if latest_execution.started_at
                        else None
                    ),
                    "completedAt": (
                        latest_execution.completed_at.isoformat()
                        if latest_execution.completed_at
                        else None
                    ),
                }
                if latest_execution
                else None
            ),
        }
