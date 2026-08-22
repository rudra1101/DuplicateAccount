from app.models.account import Account
from app.services.duplicate_detector import get_account_identity
from app.services.single_pass_duplicate_service import analyze_duplicate_decisions


def _feedback_key(application: str, account_1: Account, account_2: Account):
    key_1, key_2 = sorted(
        (get_account_identity(account_1), get_account_identity(account_2))
    )
    return (application, key_1, key_2)


def test_not_duplicate_cannot_link_blocks_transitive_regrouping():
    account_a = Account(
        id="a",
        application="ISC",
        username="john.smith",
        displayName="John Smith",
        email="john.smith@example.com",
    )
    account_b = Account(
        id="b",
        application="ISC",
        username="jsmith",
        displayName="John Smith",
        email="john.smith@example.com",
    )
    account_c = Account(
        id="c",
        application="ISC",
        username="john.s",
        displayName="John Smith",
        email="john.smith@example.com",
    )

    groups, details, _ = analyze_duplicate_decisions(
        [account_a, account_b, account_c],
        pair_feedback={
            _feedback_key("ISC", account_a, account_b): "NOT_DUPLICATE",
        },
    )

    key_a = get_account_identity(account_a)
    key_b = get_account_identity(account_b)

    for group in groups.get("ISC", []):
        detail = details[group["groupId"]]
        accounts = [detail["primaryAccount"], *[item["account"] for item in detail["duplicates"]]]
        identities = {
            get_account_identity(Account(**account))
            for account in accounts
        }
        assert not ({key_a, key_b} <= identities)


def test_not_duplicate_cannot_link_overrides_indirect_forced_duplicate_triangle():
    account_a = Account(id="a", application="ISC", username="a")
    account_b = Account(id="b", application="ISC", username="b")
    account_c = Account(id="c", application="ISC", username="c")

    feedback = {
        _feedback_key("ISC", account_a, account_b): "NOT_DUPLICATE",
        _feedback_key("ISC", account_a, account_c): "DUPLICATE",
        _feedback_key("ISC", account_b, account_c): "DUPLICATE",
    }

    groups, details, _ = analyze_duplicate_decisions(
        [account_a, account_b, account_c],
        pair_feedback=feedback,
    )

    key_a = get_account_identity(account_a)
    key_b = get_account_identity(account_b)
    for group in groups.get("ISC", []):
        detail = details[group["groupId"]]
        accounts = [detail["primaryAccount"], *[item["account"] for item in detail["duplicates"]]]
        identities = {
            get_account_identity(Account(**account))
            for account in accounts
        }
        assert not ({key_a, key_b} <= identities)
