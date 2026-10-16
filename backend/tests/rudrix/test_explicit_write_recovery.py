from types import SimpleNamespace

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.agent_core.forced_grounding import (
    primary_grounding_definition,
    safe_grounding_definitions,
)
from app.ai.fast_agent_service import _select_definitions
from app.ai.tools import create_ai_tool_registry


def _request(message: str):
    return SimpleNamespace(message=message, history=[])


def _selected_for(message: str):
    registry = create_ai_tool_registry()
    catalog = CapabilityCatalog(registry)
    selected = _select_definitions(registry.definitions(), _request(message))
    recoverable = safe_grounding_definitions(selected, catalog.capabilities())
    return selected, recoverable


def test_explicit_full_ad_aggregation_can_recover_run_integration():
    selected, recoverable = _selected_for("Run full aggregation for AD")

    selected_names = {item["name"] for item in selected}
    recoverable_names = {item["name"] for item in recoverable}

    assert "run_integration" in selected_names
    assert "run_integration" in recoverable_names

    primary = primary_grounding_definition(
        recoverable,
        "Run full aggregation for AD",
    )
    assert primary is not None
    assert primary["name"] == "run_integration"


def test_polite_explicit_delta_aggregation_can_recover_run_integration():
    _, recoverable = _selected_for("Can you run a delta aggregation for AD?")

    primary = primary_grounding_definition(
        recoverable,
        "Can you run a delta aggregation for AD?",
    )
    assert primary is not None
    assert primary["name"] == "run_integration"


def test_informational_aggregation_question_does_not_recover_write():
    _, recoverable = _selected_for("How does AD aggregation work?")

    primary = primary_grounding_definition(
        recoverable,
        "How does AD aggregation work?",
    )

    assert primary is None or primary["name"] != "run_integration"


def test_other_write_capabilities_remain_excluded_from_forced_grounding():
    registry = create_ai_tool_registry()
    catalog = CapabilityCatalog(registry)
    recoverable = safe_grounding_definitions(
        registry.definitions(),
        catalog.capabilities(),
    )
    recoverable_names = {item["name"] for item in recoverable}

    assert "run_integration" in recoverable_names
    assert "create_orphan_remediation_ticket" not in recoverable_names
    assert "review_duplicate_candidate" not in recoverable_names
    assert "create_remediation_ticket" not in recoverable_names
