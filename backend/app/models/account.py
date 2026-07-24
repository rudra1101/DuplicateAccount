from pydantic import BaseModel
from typing import Optional


class Account(BaseModel):
    account_id: str
    application: str
    username: str
    email: str
    first_name: str
    last_name: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[str] = None