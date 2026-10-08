from __future__ import annotations

from app.ai.agent_core.capabilities import CapabilityCatalog
from app.ai.tools import create_ai_tool_registry
from app.ai.tools.registry import TOOL_PERMISSION_MAP


def test_duplicate_review_action_has_dedicated_capability_and_permission():
    registry = create_ai_tool_registry()
    definitions = {item["name"]: item for item in registry.definitions()}

    assert "review_duplicate_candidate" in definitions
    assert TOOL_PERMISSION_MAP["review_duplicate_candidate"] == "duplicate.review"

    capabilities = {
        capability.name: capability
        for capability in CapabilityCatalog(registry).capabilities()
    }
    action = capabilities["review_duplicate_candidate"]
    assert action.kind.value == "WRITE"
    assert action.domain == "duplicate"


def test_duplicate_review_action_schema_accepts_grounded_candidate_id():
    registry = create_ai_tool_registry()
    definition = next(
        item for item in registry.definitions()
        if item["name"] == "review_duplicate_candidate"
    )

    properties = definition["parameters"]["properties"]
    assert "candidate_id" in properties
    assert "decision" in properties
    assert set(definition["parameters"]["required"]) == {"candidate_id", "decision"}
