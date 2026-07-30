import pandas as pd

from app.models.account import Account


def read_accounts(file) -> list[Account]:

    df = pd.read_csv(file)

    accounts = []

    for _, row in df.iterrows():

        display_name = row.get("displayName")

        if pd.isna(display_name) or display_name == "":
            first = str(row.get("first_name", "")).strip()
            last = str(row.get("last_name", "")).strip()
            display_name = f"{first} {last}".strip()

        account = Account(

            id=str(row.get("id", "")),

            application=str(row["application"]),

            username=str(row["username"]),

            displayName=display_name,

            email=str(row["email"]),

            employeeId=str(
                row.get("employeeId", row.get("employee_id", ""))
            ),

            department=str(row.get("department", "")),

            manager=str(row.get("manager", "")),

            status=str(row.get("status", "Enabled")),

            created=str(row.get("created", "")),
        )

        accounts.append(account)

    return accounts