from app.ai.duplicate_engine import duplicate_detection_engine
from app.models.account import Account
from app.services import single_pass_duplicate_service as single_pass


def test_single_pass_pipeline_detects_once_and_reuses_predictions(monkeypatch):
    accounts = [
        Account(
            id="1",
            application="ISC",
            username="john.smith",
            displayName="John Smith",
            email="john.smith@example.com",
        ),
        Account(
            id="2",
            application="ISC",
            username="john.smith",
            displayName="John Smith",
            email="john.smith@example.com",
        ),
        Account(
            id="3",
            application="ISC",
            username="jane.doe1",
            displayName="Jane Doe",
            email="",
        ),
        Account(
            id="4",
            application="ISC",
            username="jane.doe2",
            displayName="Jane Doe",
            email="",
        ),
    ]

    real_detect = single_pass.detect_application_duplicates
    calls = {"count": 0}

    def counted_detect(app_accounts):
        calls["count"] += 1
        return real_detect(app_accounts)

    monkeypatch.setattr(
        single_pass,
        "detect_application_duplicates",
        counted_detect,
    )

    groups, details, review_candidates = (
        single_pass.analyze_duplicate_decisions(accounts)
    )

    assert calls["count"] == 1
    assert len(groups["ISC"]) == 1
    assert len(details) == 1
    assert len(review_candidates) == 1
    assert review_candidates[0]["decision"] == "REVIEW"
    assert review_candidates[0]["reviewReason"] == (
        "STRONG_NAME_WITH_USERNAME_SUPPORT"
    )


def test_single_pass_pipeline_runs_once_per_application(monkeypatch):
    accounts = [
        Account(
            id="1",
            application="APP-A",
            username="alpha.user",
            displayName="Alpha User",
            email="alpha@example.com",
        ),
        Account(
            id="2",
            application="APP-A",
            username="alpha.user",
            displayName="Alpha User",
            email="alpha@example.com",
        ),
        Account(
            id="3",
            application="APP-B",
            username="beta.user",
            displayName="Beta User",
            email="beta@example.com",
        ),
        Account(
            id="4",
            application="APP-B",
            username="beta.user",
            displayName="Beta User",
            email="beta@example.com",
        ),
    ]

    calls = {"count": 0}
    real_detect = single_pass.detect_application_duplicates

    def counted_detect(app_accounts):
        calls["count"] += 1
        return real_detect(app_accounts)

    monkeypatch.setattr(
        single_pass,
        "detect_application_duplicates",
        counted_detect,
    )

    groups, _, review_candidates = (
        single_pass.analyze_duplicate_decisions(accounts)
    )

    assert calls["count"] == 2
    assert set(groups) == {"APP-A", "APP-B"}
    assert review_candidates == []
