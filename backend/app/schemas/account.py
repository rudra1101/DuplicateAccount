from pydantic import BaseModel
from typing import Optional


class Account(BaseModel):
    id: str
    application: str
    username: str
    first_name: str
    last_name: str
    email: str
    employee_id: Optional[str] = None
    department: Optional[str] = None


class DuplicateResult(BaseModel):
    account1: Account
    account2: Account
    confidence: float
    reason: list[str]