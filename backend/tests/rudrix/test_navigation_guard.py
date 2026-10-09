from __future__ import annotations

import pytest

from app.ai.tools.action_tools import NavigateAppTool


@pytest.mark.parametrize(
    ("destination", "route"),
    [
        ("dashboard", "/account-intelligence/dashboard"),
        ("integrations", "/account-intelligence/integrations"),
        ("reports", "/account-intelligence/reports"),
        ("review", "/account-intelligence/review"),
        ("remediation", "/account-intelligence/remediation"),
        ("upload", "/account-intelligence/upload"),
        ("accounts", "/account-intelligence/accounts"),
        ("duplicates", "/account-intelligence/duplicates"),
        ("settings", "/account-intelligence/settings"),
        ("ml_training", "/account-intelligence/ml-training"),
        ("users", "/platform-admin/users"),
        ("roles", "/platform-admin/roles"),
    ],
)
def test_navigation_capability_maps_destination_to_route(destination: str, route: str):
    tool = NavigateAppTool()
    result = tool.execute(
        db=object(),
        arguments={
            "destination": destination,
            "application": None,
            "integration_id": None,
        },
    )

    assert result["route"] == route
    assert result["clientAction"]["type"] == "NAVIGATE"
