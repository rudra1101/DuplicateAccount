from app.ai.duplicate_engine import duplicate_detection_engine
from app.models.account import Account
from app.services.review_candidate_service import (
    classify_prediction_decision,
    detect_review_candidates,
)


def _prediction(account_1: dict, account_2: dict):
    return duplicate_detection_engine.compare(
        account_1,
        account_2,
        include_embeddings=False,
    )


def test_strong_name_with_username_support_is_review_not_group():
    prediction = _prediction(
        {
            "id": "1",
            "application": "ISC",
            "username": "john.smith1",
            "displayName": "John Smith",
            "email": "",
        },
        {
            "id": "2",
            "application": "ISC",
            "username": "john.smith2",
            "displayName": "John Smith",
            "email": "",
        },
    )

    outcome = classify_prediction_decision(prediction)

    assert outcome["decision"] == "REVIEW"
    assert outcome["reason"] == "STRONG_NAME_WITH_USERNAME_SUPPORT"


def test_single_profiled_identifier_is_visible_for_review():
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

    candidates = detect_review_candidates(accounts)

    assert len(candidates) == 1
    assert candidates[0]["decision"] == "REVIEW"
    assert candidates[0]["reviewReason"] == "PROFILED_IDENTIFIER_REVIEW"
    assert candidates[0]["confidence"] >= 50


def test_major_identifier_conflict_is_rejected_not_reviewed():
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

    outcome = classify_prediction_decision(match)

    assert outcome["decision"] == "REJECT"
    assert outcome["reason"] == "MAJOR_CONTRADICTION"


def test_existing_high_confidence_duplicate_remains_group_decision():
    prediction = _prediction(
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
            "username": "john.smith",
            "displayName": "John Smith",
            "email": "john.smith@example.com",
        },
    )

    outcome = classify_prediction_decision(prediction)

    assert outcome["decision"] == "GROUP"
    assert outcome["reason"] == "EXACT_EMAIL_WITH_IDENTITY_SUPPORT"
