from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode

from sqlalchemy.orm import Session

from app.ai.authorization import has_rudrix_permission
from app.ai.tools.base import BaseAITool
from app.services.report_service import REPORT_CATALOG, build_report
from app.services.service_desk_service import create_ticket


REPORT_TYPES = [str(item["type"]) for item in REPORT_CATALOG]

REPORT_FILTER_KEYS = {
    "integrationId",
    "application",
    "status",
    "decision",
    "minimumConfidence",
    "reviewer",
    "search",
    "dateFrom",
    "dateTo",
}


class GenerateReportTool(BaseAITool):
    name = "generate_report"

    description = (
        "Generate a CURRENT IdentityAI CSV report from live application data. "
        "Use this only when the user explicitly asks Rudrix to generate, export, "
        "download, create, or prepare a report. Choose the best report type and "
        "apply only filters supported by the user's request. The result contains "
        "a browser download action and a small preview; do not fabricate report rows."
    )

    parameters = {
        "type": "object",
        "properties": {
            "report_type": {
                "type": "string",
                "enum": REPORT_TYPES,
                "description": "Report type to generate.",
            },
            "filters": {
                "type": "object",
                "properties": {
                    "integrationId": {"type": ["integer", "null"]},
                    "application": {"type": ["string", "null"]},
                    "status": {"type": ["string", "null"]},
                    "decision": {"type": ["string", "null"]},
                    "minimumConfidence": {"type": ["number", "null"]},
                    "reviewer": {"type": ["string", "null"]},
                    "search": {"type": ["string", "null"]},
                    "dateFrom": {"type": ["string", "null"]},
                    "dateTo": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        "required": ["report_type", "filters"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        report_type = str(arguments.get("report_type") or "").strip()
        if report_type not in REPORT_TYPES:
            raise ValueError("Unsupported report type.")

        raw_filters = arguments.get("filters") or {}
        if not isinstance(raw_filters, dict):
            raise ValueError("Report filters must be an object.")

        filters = {
            key: value
            for key, value in raw_filters.items()
            if key in REPORT_FILTER_KEYS and value not in (None, "")
        }

        report = build_report(
            db,
            report_type,
            filters,
            limit=5,
        )

        report_definition = next(
            item for item in REPORT_CATALOG if item["type"] == report_type
        )

        download_query = urlencode(
            {
                "reportType": report_type,
                **filters,
            }
        )
        download_url = f"/api/reports/rudrix-download?{download_query}"

        return {
            "message": (
                f"Generated **{report_definition['name']}** with "
                f"**{report['total']}** matching row(s). "
                f"[Download CSV]({download_url})"
            ),
            "reportType": report_type,
            "reportName": report_definition["name"],
            "total": report["total"],
            "columns": report["columns"],
            "previewRows": report["rows"],
            "downloadUrl": download_url,
            "clientAction": {
                "type": "DOWNLOAD_REPORT",
                "label": f"Download {report_definition['name']}",
                "url": download_url,
                "reportType": report_type,
                "filters": filters,
                "autoExecute": False,
            },
        }


class CreateRemediationTicketTool(BaseAITool):
    name = "create_remediation_ticket"

    description = (
        "Create a real Service Desk remediation ticket for a confirmed duplicate. "
        "Use ONLY when the user explicitly asks to create/open/raise a ticket and "
        "the remediation item ID, target account position, and DISABLE or DELETE "
        "action are known. Never guess the remediation item ID or target account. "
        "If any required detail is missing, ask the user instead of calling this tool."
    )

    parameters = {
        "type": "object",
        "properties": {
            "remediation_item_id": {
                "type": "integer",
                "minimum": 1,
                "description": "IdentityAI remediation item ID.",
            },
            "target": {
                "type": "string",
                "enum": ["ACCOUNT_1", "ACCOUNT_2"],
                "description": "Which account in the pair should be remediated.",
            },
            "action": {
                "type": "string",
                "enum": ["DISABLE", "DELETE"],
                "description": "Requested remediation action.",
            },
        },
        "required": ["remediation_item_id", "target", "action"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        item_id = int(arguments["remediation_item_id"])
        target = str(arguments["target"]).strip().upper()
        action = str(arguments["action"]).strip().upper()

        result = create_ticket(
            db,
            item_id=item_id,
            target=target,
            action=action,
            requested_by="Rudrix",
        )

        ticket_id = result.get("ticketId") or "created ticket"
        target_key = result.get("targetAccountKey") or target
        ticket_url = result.get("ticketUrl")

        message = (
            f"Created Service Desk ticket **{ticket_id}** to "
            f"**{action.lower()}** account `{target_key}`."
        )
        if ticket_url:
            message += f" [Open ticket]({ticket_url})"

        response: dict[str, Any] = {
            **result,
            "message": message,
        }

        if ticket_url:
            response["clientAction"] = {
                "type": "OPEN_EXTERNAL",
                "label": f"Open ticket {ticket_id}",
                "url": ticket_url,
                "autoExecute": False,
            }

        return response


_DESTINATIONS: dict[str, dict[str, Any]] = {
    "dashboard": {"route": "/", "label": "Dashboard", "permissions": ["dashboard.view"]},
    "duplicates": {"route": "/duplicates", "label": "Duplicate Detection", "permissions": ["duplicate.view"]},
    "review": {"route": "/review", "label": "Review Queue", "permissions": ["duplicate.review"]},
    "remediation": {"route": "/remediation", "label": "Remediation", "permissions": ["remediation.view", "remediation.history.view"]},
    "reports": {"route": "/reports", "label": "Reports", "permissions": ["report.view"]},
    "integrations": {"route": "/integrations", "label": "Integrations", "permissions": ["integration.view"]},
    "operations": {"route": "/operations", "label": "Operations", "permissions": ["operations.view"]},
    "settings": {"route": "/settings", "label": "Settings", "permissions": ["settings.manage"]},
    "knowledge": {"route": "/knowledge", "label": "Knowledge Base", "permissions": ["knowledge.view"]},
    "ml_training": {"route": "/ml-training", "label": "ML Training", "permissions": ["ml.view"]},
    "ml_evaluation": {"route": "/ml-evaluation", "label": "ML Evaluation", "permissions": ["ml.analytics.view", "ml.calibration.view"]},
    "admin": {"route": "/admin", "label": "Administration", "permissions": ["user.view", "role.view"]},
}


class NavigateAppTool(BaseAITool):
    name = "navigate_app"

    description = (
        "Navigate the authenticated user to an IdentityAI screen. Use only when "
        "the user explicitly asks to go to, open, navigate to, or show a page. "
        "This tool returns a client navigation action and validates that the user "
        "has permission to access the requested destination."
    )

    parameters = {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "enum": sorted(_DESTINATIONS.keys()),
            },
            "application": {
                "type": ["string", "null"],
                "description": "Optional application name when navigating to Review.",
            },
            "integration_id": {
                "type": ["integer", "null"],
                "minimum": 1,
                "description": "Optional integration ID used to scope Review.",
            },
        },
        "required": ["destination", "application", "integration_id"],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        del db

        destination = str(arguments.get("destination") or "").strip().lower()
        config = _DESTINATIONS.get(destination)
        if config is None:
            raise ValueError("Unsupported navigation destination.")

        permissions = list(config["permissions"])
        if not any(has_rudrix_permission(permission) for permission in permissions):
            raise PermissionError("Access denied for the requested destination.")

        route = str(config["route"])
        label = str(config["label"])

        if destination == "review":
            application = str(arguments.get("application") or "").strip()
            integration_id = arguments.get("integration_id")
            if application:
                route = f"/review/{quote(application, safe='')}"
                if integration_id:
                    route += "?" + urlencode({"integrationId": int(integration_id)})

        return {
            "message": f"[Open **{label}**]({route})",
            "destination": destination,
            "route": route,
            "clientAction": {
                "type": "NAVIGATE",
                "label": f"Open {label}",
                "route": route,
                "autoExecute": False,
            },
        }
