from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.role import RoleRecord
from app.services.rbac_service import permission_codes_for_role, seed_rbac


def test_ml_permissions_are_super_admin_only_from_system_admin_roles():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_rbac(db)

        super_admin = db.scalar(select(RoleRecord).where(RoleRecord.name == "SUPER_ADMIN"))
        admin = db.scalar(select(RoleRecord).where(RoleRecord.name == "ADMIN"))

        assert super_admin is not None
        assert admin is not None

        super_admin_permissions = set(permission_codes_for_role(super_admin))
        admin_permissions = set(permission_codes_for_role(admin))

        ml_permissions = {
            "ml.view",
            "ml.analytics.view",
            "ml.calibration.view",
            "ml.train",
        }

        assert ml_permissions.issubset(super_admin_permissions)
        assert ml_permissions.isdisjoint(admin_permissions)

        # ADMIN should still retain normal platform administration capability.
        assert "integration.view" in admin_permissions
        assert "role.view" in admin_permissions
