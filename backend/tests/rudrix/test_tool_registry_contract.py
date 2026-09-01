from app.ai.tools import create_ai_tool_registry


EXPECTED_TOOLS = {
    "get_dashboard_summary",
    "list_integrations",
    "get_integration_details",
    "get_operations_summary",
    "search_operations",
    "get_latest_execution",
    "get_execution_details",
    "get_duplicate_summary",
    "search_duplicate_groups",
    "get_duplicate_group_details",
    "get_review_statistics",
    "get_training_label_summary",
    "get_confidence_breakdown",
    "search_knowledge_base",
    "list_knowledge_documents",
    "generate_report",
    "search_remediation_items",
    "create_remediation_ticket",
    "navigate_app",
}


def test_rudrix_registry_contains_all_routing_targets():
    registry = create_ai_tool_registry()
    definitions = registry.definitions()
    names = {definition["name"] for definition in definitions}

    missing = EXPECTED_TOOLS - names
    assert not missing, f"Missing Rudrix tools: {sorted(missing)}"


def test_rudrix_registry_has_no_duplicate_tool_names():
    registry = create_ai_tool_registry()
    names = [definition["name"] for definition in registry.definitions()]

    assert len(names) == len(set(names))


def test_every_registered_tool_has_description_and_parameters():
    registry = create_ai_tool_registry()

    for definition in registry.definitions():
        assert definition.get("name")
        assert definition.get("description")
        assert isinstance(definition.get("parameters"), dict)
