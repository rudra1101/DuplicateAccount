from app.ai.tools.dashboard_tools import (
    GetDashboardSummaryTool,
)
from app.ai.tools.integration_tools import (
    ListIntegrationsTool,
)
from app.ai.tools.operations_tools import (
    GetExecutionDetailsTool,
    GetOperationsSummaryTool,
    SearchOperationsTool,
)
from app.ai.tools.registry import (
    AIToolRegistry,
)
from app.ai.tools.review_tools import (
    GetDuplicateGroupDetailsTool,
    SearchDuplicateGroupsTool,
)


def create_ai_tool_registry(
) -> AIToolRegistry:
    registry = AIToolRegistry()

    registry.register(
        GetDashboardSummaryTool()
    )

    registry.register(
        GetOperationsSummaryTool()
    )

    registry.register(
        SearchOperationsTool()
    )

    registry.register(
        GetExecutionDetailsTool()
    )

    registry.register(
        ListIntegrationsTool()
    )

    registry.register(
        SearchDuplicateGroupsTool()
    )

    registry.register(
        GetDuplicateGroupDetailsTool()
    )

    return registry