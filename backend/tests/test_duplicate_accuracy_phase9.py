from app.models.account import Account
from app.services.duplicate_detector import get_account_identity
from app.services.single_pass_duplicate_service import analyze_duplicate_decisions


def _feedback_key(application: str, account_1: Account, account_2: Account):
    key_1, key_2 = sorted(
        (get_account_identity(account_1), get_account_identity(account_2))
    )
    return (application, key_1, key_2)


def test_reviewer_confirmed_duplicate_is_grouped_on_next_scan_even_without_model_match():
    account_1 = Account(
        id="1",
        application="ISC",
        username="alpha.one",
        displayName="Alpha One",
        email="alpha.one@example.com",
    )
    account_2 = Account(
        id="2",
        application="ISC",
        username="completely.different",
        displayName="Different Person",
        email="different@example.org",
    )

    groups, details, review_candidates = analyze_duplicate_decisions(
        [account_1, account_2],
        pair_feedback={
            _feedback_key("ISC", account_1, account_2): "DUPLICATE",
        },
    )

    assert len(groups["ISC"]) == 1
    assert groups["ISC"][0]["duplicates"] == 1
    group_id = groups["ISC"][0]["groupId"]
    assert details[group_id]["duplicates"][0]["groupingEvidence"] == (
        "REVIEWER_CONFIRMED_DUPLICATE"
    )
    assert review_candidates == []


def test_reviewer_confirmed_not_duplicate_is_suppressed_on_next_scan():
    account_1 = Account(
        id="1",
        application="ISC",
        username="john.smith",
        displayName="John Smith",
        email="john.smith@example.com",
    )
    account_2 = Account(
        id="2",
        application="ISC",
        username="john.smith",
        displayName="John Smith",
        email="john.smith@example.com",
    )

    groups, _, review_candidates = analyze_duplicate_decisions(
        [account_1, account_2],
        pair_feedback={
            _feedback_key("ISC", account_1, account_2): "NOT_DUPLICATE",
        },
    )

    assert groups.get("ISC", []) == []
    assert review_candidates == []
