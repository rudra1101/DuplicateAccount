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
    GetDuplicateGroupDetailsTool,
    GetDuplicateSummaryTool,
    GetReviewStatisticsTool,
    SearchDuplicateGroupsTool,
    GetConfidenceBreakdownTool,

)
from app.ai.tools.training_tools import (
    GetTrainingLabelSummaryTool,
)

from app.ai.tools.knowledge_tools import (
    SearchKnowledgeBaseTool,
    ListKnowledgeDocumentsTool,
)


def create_ai_tool_registry() -> AIToolRegistry:
    registry = AIToolRegistry()

    registry.register(GetDashboardSummaryTool())

    registry.register(ListIntegrationsTool())
    registry.register(GetIntegrationDetailsTool())

    registry.register(GetOperationsSummaryTool())
    registry.register(SearchOperationsTool())
    registry.register(GetLatestExecutionTool())
    registry.register(GetExecutionDetailsTool())

    registry.register(GetDuplicateSummaryTool())
    registry.register(SearchDuplicateGroupsTool())
    registry.register(GetDuplicateGroupDetailsTool())
    registry.register(GetReviewStatisticsTool())

    registry.register(GetTrainingLabelSummaryTool())
    registry.register(GetConfidenceBreakdownTool())
    registry.register(SearchKnowledgeBaseTool())
    registry.register(ListKnowledgeDocumentsTool())


    return registry
