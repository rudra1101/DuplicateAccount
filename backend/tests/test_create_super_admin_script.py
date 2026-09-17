from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.auth.security import verify_password
from app.database.base import Base
from app.db_models.role import RoleRecord
from app.db_models.user import UserRecord
from app.scripts.create_super_admin import create_super_admin


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_super_admin_bootstraps_role_and_hashes_password():
    with _session() as db:
        user = create_super_admin(
            db,
            username="superadmin",
            email="superadmin@identityai.local",
            full_name="Super Admin",
            password="SuperAdmin@12345",
        )

        assert user.role == "SUPER_ADMIN"
        assert user.is_active is True
        assert verify_password("SuperAdmin@12345", user.password_hash)

        role = db.scalar(select(RoleRecord).where(RoleRecord.name == "SUPER_ADMIN"))
        assert role is not None


def test_create_super_admin_rejects_duplicate_username_or_email():
    with _session() as db:
        create_super_admin(
            db,
            username="superadmin",
            email="superadmin@identityai.local",
            full_name="Super Admin",
            password="SuperAdmin@12345",
        )

        try:
            create_super_admin(
                db,
                username="superadmin",
                email="other@identityai.local",
                full_name="Other Super Admin",
                password="AnotherPassword@123",
            )
        except ValueError as exc:
            assert "username" in str(exc).lower()
        else:
            raise AssertionError("Expected duplicate username to be rejected")

        try:
            create_super_admin(
                db,
                username="other-superadmin",
                email="superadmin@identityai.local",
                full_name="Other Super Admin",
                password="AnotherPassword@123",
            )
        except ValueError as exc:
            assert "email" in str(exc).lower()
        else:
            raise AssertionError("Expected duplicate email to be rejected")


def test_create_super_admin_requires_minimum_password_length():
    with _session() as db:
        try:
            create_super_admin(
                db,
                username="superadmin",
                email="superadmin@identityai.local",
                full_name="Super Admin",
                password="short",
            )
        except ValueError as exc:
            assert "12" in str(exc)
        else:
            raise AssertionError("Expected short password to be rejected")
