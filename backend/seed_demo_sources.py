from pathlib import Path

from sqlalchemy import select

from app.database.session import SessionLocal
from app.db_models.integration import IntegrationRecord
from app.schemas.application_schema import IntegrationApplicationsPayload
from app.schemas.correlation_policy import CorrelationPolicyInput, CorrelationPolicyUpdate
from app.services.application_schema_service import replace_integration_applications
from app.services.correlation_policy_service import (
    create_policy,
    get_policy_for_account_integration,
    update_policy,
)


BASE_DIR = Path(__file__).resolve().parent
HR_FOLDER = (BASE_DIR / "sample_sources" / "hr").resolve()
AD_FOLDER = (BASE_DIR / "sample_sources" / "ad").resolve()


def get_or_create_integration(db, *, name: str, purpose: str, folder: Path) -> IntegrationRecord:
    integration = db.scalar(select(IntegrationRecord).where(IntegrationRecord.name == name))
    configuration = {
        "folderPath": str(folder),
        "filePattern": "*.csv",
        "selectionStrategy": "LATEST",
        "delimiter": ",",
        "encoding": "utf-8-sig",
    }

    if integration is None:
        integration = IntegrationRecord(
            name=name,
            connector_type="LOCAL",
            source_purpose=purpose,
            description=(
                "Demo authoritative HR source for orphan-account testing."
                if purpose == "AUTHORITATIVE"
                else "Demo Active Directory account source for orphan-account testing."
            ),
            configuration=configuration,
            enabled=True,
        )
        db.add(integration)
        db.commit()
        db.refresh(integration)
    else:
        integration.connector_type = "LOCAL"
        integration.source_purpose = purpose
        integration.configuration = configuration
        integration.enabled = True
        db.commit()
        db.refresh(integration)

    return integration


def configure_hr_schema(db, integration: IntegrationRecord) -> None:
    payload = IntegrationApplicationsPayload.model_validate(
        {
            "applications": [
                {
                    "name": "Workday HR",
                    "displayName": "Workday HR",
                    "objectType": "identity",
                    "enabled": True,
                    "schemaName": "Workday Worker Schema",
                    "attributes": [
                        {"name": "application", "position": 0},
                        {"name": "id", "position": 1},
                        {"name": "workerId", "position": 2},
                        {"name": "employeeId", "position": 3},
                        {"name": "username", "position": 4},
                        {"name": "networkId", "position": 5},
                        {"name": "email", "position": 6},
                        {"name": "workEmail", "position": 7},
                        {"name": "displayName", "position": 8},
                        {"name": "status", "position": 9},
                        {"name": "department", "position": 10},
                    ],
                }
            ]
        }
    )
    replace_integration_applications(db, integration, payload)


def configure_ad_schema(db, integration: IntegrationRecord) -> None:
    payload = IntegrationApplicationsPayload.model_validate(
        {
            "applications": [
                {
                    "name": "Active Directory",
                    "displayName": "Active Directory",
                    "objectType": "account",
                    "enabled": True,
                    "schemaName": "AD Account Schema",
                    "attributes": [
                        {"name": "application", "position": 0},
                        {"name": "id", "position": 1},
                        {"name": "employeeId", "position": 2},
                        {"name": "samAccountName", "position": 3},
                        {"name": "mail", "position": 4},
                        {"name": "displayName", "position": 5},
                        {"name": "status", "position": 6},
                        {"name": "privileged", "position": 7},
                        {"name": "accountType", "position": 8},
                        {"name": "owner", "position": 9},
                    ],
                }
            ]
        }
    )
    replace_integration_applications(db, integration, payload)


def configure_correlation_policy(db, ad: IntegrationRecord, hr: IntegrationRecord) -> None:
    policy_payload = {
        "name": "Active Directory to Workday HR",
        "authoritativeIntegrationId": hr.id,
        "strategy": "FIRST_MATCH_WINS",
        "enabled": True,
        "rules": [
            {
                "priority": 1,
                "accountAttribute": "employeeId",
                "identityAttribute": "workerId",
                "matchType": "EXACT",
                "enabled": True,
            },
            {
                "priority": 2,
                "accountAttribute": "mail",
                "identityAttribute": "workEmail",
                "matchType": "CASE_INSENSITIVE",
                "enabled": True,
            },
            {
                "priority": 3,
                "accountAttribute": "samAccountName",
                "identityAttribute": "networkId",
                "matchType": "CASE_INSENSITIVE",
                "enabled": True,
            },
        ],
    }

    existing = get_policy_for_account_integration(db, ad.id)
    if existing is None:
        create_policy(
            db,
            CorrelationPolicyInput.model_validate(
                {
                    "accountIntegrationId": ad.id,
                    **policy_payload,
                }
            ),
        )
    else:
        update_policy(db, existing, CorrelationPolicyUpdate.model_validate(policy_payload))


def main() -> None:
    with SessionLocal() as db:
        hr = get_or_create_integration(
            db,
            name="Demo Workday HR",
            purpose="AUTHORITATIVE",
            folder=HR_FOLDER,
        )
        ad = get_or_create_integration(
            db,
            name="Demo Active Directory",
            purpose="ACCOUNT",
            folder=AD_FOLDER,
        )

        configure_hr_schema(db, hr)
        configure_ad_schema(db, ad)
        configure_correlation_policy(db, ad, hr)

        print("Created/updated demo sources:")
        print(f"  AUTHORITATIVE: {hr.name} (id={hr.id})")
        print(f"  ACCOUNT:       {ad.name} (id={ad.id})")
        print("  Correlation:   employeeId -> workerId, mail -> workEmail, samAccountName -> networkId")
        print("\nRun the authoritative source first, then run the account source.")


if __name__ == "__main__":
    main()
