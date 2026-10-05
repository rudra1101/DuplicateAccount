from __future__ import annotations

import pytest

from app.api.chat_stream import _requested_navigation_destination


@pytest.mark.parametrize(
    ("message", "destination", "route"),
    [
        ("Open dashboard", "dashboard", "/account-intelligence/dashboard"),
        ("Take me to integrations", "integrations", "/account-intelligence/integrations"),
        ("Open the reports page", "reports", "/account-intelligence/reports"),
        ("Show the review queue", "review", "/account-intelligence/review"),
        ("Go to remediation", "remediation", "/account-intelligence/remediation"),
        ("Open accounts", "accounts", "/account-intelligence/accounts"),
        ("Navigate to duplicate detection", "duplicates", "/account-intelligence/duplicates"),
        ("Open settings", "settings", "/account-intelligence/settings"),
        ("Take me to ML training", "ml_training", "/account-intelligence/ml-training"),
        ("Open user management", "users", "/platform-admin/users"),
        ("Open role management", "roles", "/platform-admin/roles"),
    ],
)
def test_navigation_destination_is_deterministic(
    message: str,
    destination: str,
    route: str,
):
    resolved = _requested_navigation_destination(message)

    assert resolved is not None
    assert resolved[0] == destination
    assert resolved[1] == route


def test_non_navigation_request_is_not_rewritten():
    assert _requested_navigation_destination("How many reports do we have?") is None
