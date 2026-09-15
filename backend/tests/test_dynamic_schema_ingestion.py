from io import BytesIO

import pytest

from app.services.account_loader import load_uploaded_accounts


def test_dynamic_schema_accepts_adp_style_worker_feed_without_username() -> None:
    content = (
        "associateOID,workerID,legalGivenName,legalFamilyName,workerStatus\n"
        "AOID-123,W00123,Rudra,Shankar,Active\n"
    ).encode("utf-8")

    records = load_uploaded_accounts(
        BytesIO(content),
        default_application="ADP Workers",
        allow_dynamic_schema=True,
        encoding="utf-8",
    )

    assert len(records) == 1
    assert records[0].employeeId == "W00123"
    assert records[0].username == "W00123"
    assert records[0].rawAttributes["associateOID"] == "AOID-123"
    assert records[0].rawAttributes["workerStatus"] == "Active"


def test_dynamic_schema_accepts_completely_arbitrary_customer_columns() -> None:
    content = (
        "personRef,orgCode,lifecycleFlag,customValue\n"
        "P-7788,ORG-X,LIVE,anything\n"
    ).encode("utf-8")

    records = load_uploaded_accounts(
        BytesIO(content),
        default_application="Custom HR",
        allow_dynamic_schema=True,
        encoding="utf-8",
    )

    assert len(records) == 1
    assert records[0].application == "Custom HR"
    assert records[0].username.startswith("record-2-")
    assert records[0].id.startswith("record-2-")
    assert records[0].rawAttributes == {
        "personRef": "P-7788",
        "orgCode": "ORG-X",
        "lifecycleFlag": "LIVE",
        "customValue": "anything",
    }


def test_manual_upload_still_requires_historical_columns() -> None:
    content = b"personRef,orgCode\nP-1,ORG-X\n"

    with pytest.raises(ValueError, match="Missing required columns"):
        load_uploaded_accounts(BytesIO(content), encoding="utf-8")
