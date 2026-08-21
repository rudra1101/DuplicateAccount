from app.ai.duplicate_engine import duplicate_detection_engine
from app.models.account import Account
from app.services.duplicate_detector import (
    detect_duplicate_groups,
    get_grouping_edge_reason,
)


def test_dynamic_identifier_with_contact_support_forms_group():
    accounts = [
        Account(
            id="1",
            application="ISC",
            username="alpha.one",
            rawAttributes={
                "payrollNumber": "P100",
                "alternateEmail": "person@example.com",
            },
        ),
        Account(
            id="2",
            application="ISC",
            username="totally.different",
            rawAttributes={
                "payrollNumber": "P100",
                "alternateEmail": "person@example.com",
            },
        ),
        Account(
            id="3",
            application="ISC",
            username="third.account",
            rawAttributes={
                "payrollNumber": "P200",
                "alternateEmail": "third@example.com",
            },
        ),
    ]

    results, details = detect_duplicate_groups(accounts)

    assert "ISC" in results
    assert len(results["ISC"]) == 1
    assert results["ISC"][0]["duplicates"] == 1

    group_id = results["ISC"][0]["groupId"]
    duplicate = details[group_id]["duplicates"][0]
    assert duplicate["groupingEvidence"] == "DYNAMIC_IDENTIFIER_WITH_IDENTITY_SUPPORT"


def test_single_dynamic_identifier_without_support_does_not_form_group():
    accounts = [
        Account(
            id="1",
            application="ISC",
            username="alpha.one",
            rawAttributes={"payrollNumber": "P100"},
        ),
        Account(
            id="2",
            application="ISC",
            username="totally.different",
            rawAttributes={"payrollNumber": "P100"},
        ),
        Account(
            id="3",
            application="ISC",
            username="third.account",
            rawAttributes={"payrollNumber": "P200"},
        ),
    ]

    results, details = detect_duplicate_groups(accounts)

    assert results == {}
    assert details == {}


def test_conflicting_profiled_identifier_blocks_grouping_edge():
    accounts = [
        {
            "id": "1",
            "application": "ISC",
            "username": "alpha.one",
            "rawAttributes": {
                "payrollNumber": "P100",
                "badgeId": "B1",
                "alternateEmail": "person@example.com",
            },
        },
        {
            "id": "2",
            "application": "ISC",
            "username": "beta.two",
            "rawAttributes": {
                "payrollNumber": "P100",
                "badgeId": "B2",
                "alternateEmail": "person@example.com",
            },
        },
        {
            "id": "3",
            "application": "ISC",
            "username": "gamma.three",
            "rawAttributes": {
                "payrollNumber": "P200",
                "badgeId": "B1",
                "alternateEmail": "gamma@example.com",
            },
        },
        {
            "id": "4",
            "application": "ISC",
            "username": "delta.four",
            "rawAttributes": {
                "payrollNumber": "P300",
                "badgeId": "B2",
                "alternateEmail": "delta@example.com",
            },
        },
    ]

    predictions = duplicate_detection_engine.detect(
        accounts,
        minimum_confidence=20,
        include_embeddings=False,
        minimum_blocking_score=4.0,
    )

    match = next(
        prediction
        for prediction in predictions
        if {prediction.account_1_id, prediction.account_2_id} == {"1", "2"}
    )

    assert match.features.dynamic_identifier_matches >= 1
    assert match.features.dynamic_identifier_conflicts >= 1
    assert get_grouping_edge_reason(match) is None
