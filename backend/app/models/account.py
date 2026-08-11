from pydantic import BaseModel


class Account(BaseModel):
    id: str | None = None

    application: str

    username: str

    displayName: str = ""

    email: str

    employeeId: str | None = None

    department: str | None = None

    manager: str | None = None

    status: str | None = None

    created: str | None = None