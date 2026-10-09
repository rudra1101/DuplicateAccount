from __future__ import annotations

from typing import Any

from rapidfuzz.fuzz import token_set_ratio
from sqlalchemy.orm import Session

from app.ai.tools.base import BaseAITool
from app.services.report_service import REPORT_CATALOG


PRODUCT_AREAS: tuple[dict[str, Any], ...] = (
    {
        "area": "Dashboard",
        "summary": "IdentityAI dashboard metrics and high-level identity hygiene posture, including integrations, duplicate accounts, and current system summaries.",
    },
    {
        "area": "Integrations and aggregation",
        "summary": "IdentityAI connects identity/account sources, stores integration configuration, runs source operations and aggregations, and exposes execution status and failures.",
    },
    {
        "area": "Accounts and correlation",
        "summary": "IdentityAI inventories source accounts and correlates them to identities using configured correlation policy evidence. Accounts can be searched by business-facing identifiers such as username, email, employee ID, display name, and native identity.",
    },
    {
        "area": "Orphan accounts",
        "summary": "IdentityAI persists current orphan state and correlation evidence such as orphan type, reason, policy, strategy, correlation attempts, and matched identity when available.",
    },
    {
        "area": "Duplicate accounts",
        "summary": "IdentityAI detects duplicate-account groups and candidates, exposes confidence and matching evidence, and supports review decisions on grounded candidates.",
    },
    {
        "area": "Remediation",
        "summary": "IdentityAI tracks remediation items for duplicate accounts and can create Service Desk tickets for explicit targets/actions when the logged-in user has permission.",
    },
    {
        "area": "Reports",
        "summary": "IdentityAI can build filtered live-data reports and expose CSV downloads. Report generation must use current application data rather than invented rows.",
    },
    {
        "area": "Operations",
        "summary": "IdentityAI exposes execution history, latest operation state, operation search, and execution details for troubleshooting integrations and jobs.",
    },
    {
        "area": "Knowledge base",
        "summary": "IdentityAI supports uploaded manuals, policies, runbooks, procedures, and other documents through semantic RAG retrieval. Uploaded knowledge is distinct from live application state.",
    },
    {
        "area": "RBAC and administration",
        "summary": "Rudrix follows IdentityAI permissions. Capabilities are hidden or blocked when the logged-in user lacks the required permission, and write/destructive actions require explicit intent.",
    },
    {
        "area": "Machine learning",
        "summary": "IdentityAI exposes ML/training label summaries used by the duplicate intelligence workflow when the user has ML access.",
    },
)


class SearchIdentityAIProductKnowledgeTool(BaseAITool):
    name = "search_identityai_product_knowledge"
    description = (
        "Search BUILT-IN IdentityAI product knowledge: feature areas, what the product can do, "
        "how major workflows fit together, and which live capabilities are available to the "
        "current user. Use this for IdentityAI product questions that are not asking for current "
        "records. For organization-specific manuals/policies use the uploaded knowledge base."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language IdentityAI product question or topic.",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def execute(self, *, db: Session, arguments: dict[str, Any]) -> Any:
        del db
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("Product knowledge query cannot be empty.")
        limit = max(1, min(int(arguments.get("limit") or 6), 10))

        # Import lazily to avoid a module-import cycle while the registry is built.
        from app.ai.tools import create_ai_tool_registry

        definitions = create_ai_tool_registry().definitions()
        capability_rows: list[dict[str, Any]] = []
        for definition in definitions:
            name = str(definition.get("name") or "")
            if name == self.name:
                continue
            description = str(definition.get("description") or "")
            searchable = f"{name.replace('_', ' ')} {description}"
            score = token_set_ratio(query, searchable)
            capability_rows.append(
                {
                    "name": name,
                    "description": description,
                    "relevance": round(score / 100.0, 3),
                }
            )

        area_rows = []
        for area in PRODUCT_AREAS:
            searchable = f"{area['area']} {area['summary']}"
            area_rows.append(
                {
                    **area,
                    "relevance": round(token_set_ratio(query, searchable) / 100.0, 3),
                }
            )

        capability_rows.sort(key=lambda item: item["relevance"], reverse=True)
        area_rows.sort(key=lambda item: item["relevance"], reverse=True)

        return {
            "query": query,
            "productAreas": area_rows[:limit],
            "authorizedCapabilities": capability_rows[:limit],
            "reportTypes": [
                {"type": item.get("type"), "name": item.get("name")}
                for item in REPORT_CATALOG
            ],
            "grounding": (
                "This is built-in IdentityAI product knowledge plus the current user's "
                "authorized Rudrix capability contracts. It is not live record data."
            ),
        }
