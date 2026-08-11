import json

from app.ai.duplicate_engine import (
    duplicate_detection_engine,
)


account_1 = {
    "id": "HR-100",
    "application": "Workday",
    "username": (
        "william.thompson"
    ),
    "displayName": (
        "William Thompson"
    ),
    "email": (
        "william.thompson"
        "@company.com"
    ),
    "employeeId": "EMP9001",
    "department": (
        "Human Resources"
    ),
    "manager": "Anita Sharma",
    "status": "Active",
}

account_2 = {
    "id": "AD-900",
    "application": (
        "Active Directory"
    ),
    "username": "bill.thompson",
    "displayName": (
        "Bill Thompson"
    ),
    "email": (
        "bill.thompson"
        "@company.com"
    ),
    "employeeId": "EMP9001",
    "department": "HR",
    "manager": "Anita Sharma",
    "status": "Enabled",
}


prediction = (
    duplicate_detection_engine
    .compare(
        account_1,
        account_2,
        include_embeddings=True,
    )
)


print(
    json.dumps(
        prediction.to_dict(
            include_accounts=True,
        ),
        indent=2,
    )
)