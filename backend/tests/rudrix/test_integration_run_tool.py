from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.agent_core.models import CapabilityKind
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.integration_tools import RunIntegrationTool
from app.ai.tools.registry import TOOL_PERMISSION_MAP


def _integration(*, enabled: bool = True):
    return SimpleNamespace(
        id=7,
        name="Active Directory",
        connector_type="LOCAL",
        source_purpose="ACCOUNT_SOURCE",
        description=None,
        configuration={},
        enabled=enabled,
        created_at=None,
        updated_at=None,
        schedule=None,
    )


def test_run_integration_executes_shared_service_for_explicit_source():
    db = Mock()
    integration = _integration()
    execution = {"id": 91, "status": "SUCCESS", "accountsScanned": 19}

    with patch(
        "app.ai.tools.integration_tools._find_integration",
        return_value=integration,
    ), patch(
        "app.ai.tools.integration_tools.run_integration",
        return_value=execution,
    ) as run:
        result = RunIntegrationTool().execute(
            db=db,
            arguments={"integration": "AD", "aggregation_type": "FULL"},
        )

    run.assert_called_once_with(
        db=db,
        integration=integration,
        aggregation_type="FULL",
    )
    assert result["started"] is True
    assert result["execution"] == execution
    assert result["aggregationType"] == "FULL"


def test_run_integration_does_not_execute_disabled_source():
    db = Mock()
    integration = _integration(enabled=False)

    with patch(
        "app.ai.tools.integration_tools._find_integration",
        return_value=integration,
    ), patch("app.ai.tools.integration_tools.run_integration") as run:
        result = RunIntegrationTool().execute(
            db=db,
            arguments={"integration": "Active Directory"},
        )

    run.assert_not_called()
    assert result["started"] is False
    assert "disabled" in result["message"].lower()


def test_run_integration_is_rbac_protected_write_capability():
    registry = create_ai_tool_registry()
    capabilities = {item.name: item for item in CapabilityCatalog(registry).capabilities()}

    assert TOOL_PERMISSION_MAP["run_integration"] == "integration.run"
    assert capabilities["run_integration"].kind == CapabilityKind.WRITE
    assert capabilities["run_integration"].destructive is False
