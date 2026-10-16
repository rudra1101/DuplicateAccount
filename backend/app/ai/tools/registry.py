from typing import Any

from sqlalchemy.orm import Session

from app.ai.authorization import (
    get_rudrix_permissions,
    has_rudrix_permission,
)
from app.ai.tools.base import BaseAITool


AUTHENTICATED_TOOL = "__authenticated__"

TOOL_PERMISSION_MAP: dict[str, str] = {
    "get_dashboard_summary": "dashboard.view",
    "list_integrations": "integration.view",
    "get_integration_details": "integration.view",
    "run_integration": "integration.run",
    "investigate_accounts": "integration.view",
    "search_orphan_accounts": "integration.view",
    "explain_orphan_account": "integration.view",
    "create_orphan_remediation_ticket": "remediation.manage",
    "get_operations_summary": "operations.view",
    "search_operations": "operations.view",
    "get_latest_execution": "operations.view",
    "get_execution_details": "operations.view",
    "get_duplicate_summary": "duplicate.view",
    "search_duplicate_groups": "duplicate.view",
    "get_duplicate_group_details": "duplicate.view",
    "get_review_statistics": "duplicate.view",
    "review_duplicate_candidate": "duplicate.review",
    "get_confidence_breakdown": "duplicate.view",
    "get_training_label_summary": "ml.view",
    "search_knowledge_base": "knowledge.view",
    "list_knowledge_documents": "knowledge.view",
    "search_identityai_product_knowledge": AUTHENTICATED_TOOL,
    "generate_report": "report.view",
    "search_remediation_items": "remediation.view",
    "create_remediation_ticket": "remediation.manage",
    "navigate_app": AUTHENTICATED_TOOL,
}


class AIToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseAITool] = {}

    def register(self, tool: BaseAITool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"AI tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def _is_authorized(self, name: str) -> bool:
        permissions = get_rudrix_permissions()
        if permissions is None:
            return True
        permission = TOOL_PERMISSION_MAP.get(name)
        if permission is None:
            return False
        if permission == AUTHENTICATED_TOOL:
            return True
        return has_rudrix_permission(permission)

    def get(self, name: str) -> BaseAITool:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown AI tool: {name}")
        if not self._is_authorized(name):
            raise PermissionError("Access denied.")
        return tool

    def definitions(self) -> list[dict[str, Any]]:
        return [
            tool.to_openai_definition()
            for tool in self._tools.values()
            if self._is_authorized(tool.name)
        ]

    def execute(
        self,
        *,
        name: str,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:
        tool = self.get(name)
        return tool.execute(db=db, arguments=arguments)
