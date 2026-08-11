import json

from app.ai.duplicate_engine import (
    duplicate_detection_engine,
)


accounts = [
    {
        "id": "AD-101",
        "application": (
            "Active Directory"
        ),
        "username": "john.smith",
        "displayName": "John Smith",
        "email": (
            "john.smith@company.com"
        ),
        "employeeId": "EMP1001",
        "department": "Finance",
        "manager": "Anil Kumar",
        "phone": "+91 98765 43210",
        "status": "Active",
    },
    {
        "id": "ENTRA-902",
        "application": "Entra ID",
        "username": "jsmith",
        "displayName": "John Smith",
        "email": (
            "john.smith@company.com"
        ),
        "employeeId": "EMP1001",
        "department": "Finance",
        "manager": "Anil Kumar",
        "phone": "9876543210",
        "status": "Enabled",
    },
]


predictions = (
    duplicate_detection_engine.detect(
        accounts,
        minimum_confidence=70,
        cross_application_only=True,
    )
)


print(
    json.dumps(
        [
            prediction.to_dict(
                include_accounts=True,
                include_raw_accounts=False,
            )
            for prediction in predictions
        ],
        indent=2,
    )
)