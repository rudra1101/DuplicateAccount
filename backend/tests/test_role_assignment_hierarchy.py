from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.api.users import validate_assignable_role, validate_manageable_account
from app.database.base import Base
from app.services.rbac_service import seed_rbac


def _actor(role: str):
    return SimpleNamespace(role=role)


def test_admin_cannot_assign_super_admin_but_super_admin_and_owner_can():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_rbac(db)

        with pytest.raises(HTTPException) as exc_info:
            validate_assignable_role(db, "SUPER_ADMIN", _actor("ADMIN"))
        assert exc_info.value.status_code == 403

        assert validate_assignable_role(db, "SUPER_ADMIN", _actor("SUPER_ADMIN")).name == "SUPER_ADMIN"
        assert validate_assignable_role(db, "SUPER_ADMIN", _actor("OWNER")).name == "SUPER_ADMIN"


def test_admin_cannot_change_existing_super_admin_account():
    with pytest.raises(HTTPException) as exc_info:
        validate_manageable_account("SUPER_ADMIN", _actor("ADMIN"))
    assert exc_info.value.status_code == 403

    validate_manageable_account("SUPER_ADMIN", _actor("SUPER_ADMIN"))
    validate_manageable_account("SUPER_ADMIN", _actor("OWNER"))


def test_owner_role_remains_owner_only():
    with pytest.raises(HTTPException) as exc_info:
        validate_manageable_account("OWNER", _actor("SUPER_ADMIN"))
    assert exc_info.value.status_code == 403
