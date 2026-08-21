from app.ai.duplicate_engine import duplicate_detection_engine
from app.services.duplicate_detector import build_grouping_diagnostic


def test_grouping_diagnostic_explains_below_threshold_dynamic_identifier():
    accounts = [
        {
            "id": "1",
            "application": "ISC",
            "username": "alpha.one",
            "rawAttributes": {"payrollNumber": "P100"},
        },
        {
            "id": "2",
            "application": "ISC",
            "username": "totally.different",
            "rawAttributes": {"payrollNumber": "P100"},
        },
        {
            "id": "3",
            "application": "ISC",
            "username": "third.account",
            "rawAttributes": {"payrollNumber": "P200"},
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

    diagnostic = build_grouping_diagnostic(match)

    assert diagnostic["result"] == "REJECTED"
    assert diagnostic["edgeReason"] is None
    assert diagnostic["reason"] in {
        "BELOW_NON_AUTHORITATIVE_THRESHOLD",
        "DYNAMIC_IDENTIFIER_BELOW_GROUP_THRESHOLD",
    }
    assert diagnostic["evidence"]["dynamicIdentifierMatches"] >= 1


def test_grouping_diagnostic_explains_dynamic_identifier_conflict():
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

    diagnostic = build_grouping_diagnostic(match)

    assert diagnostic["result"] == "REJECTED"
    assert diagnostic["reason"] == "MAJOR_CONTRADICTION"
    assert diagnostic["evidence"]["dynamicIdentifierConflicts"] >= 1


def test_grouping_diagnostic_reports_accepted_edge_reason():
    prediction = duplicate_detection_engine.compare(
        {
            "id": "1",
            "application": "ISC",
            "username": "john.smith",
            "displayName": "John Smith",
            "email": "john.smith@example.com",
        },
        {
            "id": "2",
            "application": "ISC",
            "username": "jsmith",
            "displayName": "John Smith",
            "email": "john.smith@example.com",
        },
        include_embeddings=False,
    )

    diagnostic = build_grouping_diagnostic(prediction)

    assert diagnostic["result"] == "ACCEPTED"
    assert diagnostic["reason"] == "EXACT_EMAIL_WITH_IDENTITY_SUPPORT"
    assert diagnostic["edgeReason"] == "EXACT_EMAIL_WITH_IDENTITY_SUPPORT"
    assert diagnostic["evidence"]["emailExact"] is True
