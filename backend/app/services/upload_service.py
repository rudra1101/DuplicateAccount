import pandas as pd

from app.schemas.account import Account


def read_accounts(file) -> list[Account]:

    df = pd.read_csv(file)

    accounts = []

    for _, row in df.iterrows():

        account = Account(

            id=str(row.get("id", "")),

            application=row["application"],

            username=row["username"],

            first_name=row["first_name"],

            last_name=row["last_name"],

            email=row["email"],

            employee_id=row.get("employee_id"),

            department=row.get("department")

        )

        accounts.append(account)

    return accounts