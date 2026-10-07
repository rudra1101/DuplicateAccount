from app.ai.tools.action_tools import (
    GenerateReportTool,
    NavigateAppTool,
)
from app.ai.tools.account_investigation_tools import (
    InvestigateAccountsTool,
)
from app.ai.tools.account_resolution_tools import (
    GroundedCreateRemediationTicketTool,
    GroundedDuplicateGroupDetailsTool,
    GroundedReviewOperationsTool,
    GroundedSearchDuplicateGroupsTool,
)
from app.ai.tools.dashboard_tools import (
    GetDashboardSummaryTool,
)
from app.ai.tools.integration_tools import (
    GetIntegrationDetailsTool,
    ListIntegrationsTool,
)
from app.ai.tools.operations_tools import (
    GetExecutionDetailsTool,
    GetLatestExecutionTool,
    GetOperationsSummaryTool,
    SearchOperationsTool,
)
from app.ai.tools.registry import AIToolRegistry
from app.ai.tools.review_tools import (
    GetConfidenceBreakdownTool,
    GetDuplicateSummaryTool,
)
from app.ai.tools.training_tools import (
    GetTrainingLabelSummaryTool,
)
from app.ai.tools.knowledge_tools import (
    ListKnowledgeDocumentsTool,
    SearchKnowledgeBaseTool,
)
from app.ai.tools.remediation_action_tools import (
    RudrixRemediationOperationsTool,
)


def create_ai_tool_registry() -> AIToolRegistry:
    registry = AIToolRegistry()

    registry.register(GetDashboardSummaryTool())

    registry.register(ListIntegrationsTool())
    registry.register(GetIntegrationDetailsTool())
    registry.register(InvestigateAccountsTool())

    registry.register(GetOperationsSummaryTool())
    registry.register(SearchOperationsTool())
    registry.register(GetLatestExecutionTool())
    registry.register(GetExecutionDetailsTool())

    registry.register(GetDuplicateSummaryTool())
    registry.register(GroundedSearchDuplicateGroupsTool())
    registry.register(GroundedDuplicateGroupDetailsTool())
    registry.register(GroundedReviewOperationsTool())

    registry.register(GetTrainingLabelSummaryTool())
    registry.register(GetConfidenceBreakdownTool())
    registry.register(SearchKnowledgeBaseTool())
    registry.register(ListKnowledgeDocumentsTool())

    registry.register(GenerateReportTool())
    registry.register(RudrixRemediationOperationsTool())
    registry.register(GroundedCreateRemediationTicketTool())
    registry.register(NavigateAppTool())

    return registry
