from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.role import RoleRecord
from app.services.rbac_service import permission_codes_for_role, seed_rbac


DOMAIN_PERMISSIONS = {
    "domain.account_intelligence.view",
    "domain.account_heatmap.view",
    "domain.non_human_identity.view",
}


def test_domain_permissions_are_seeded_for_system_roles():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_rbac(db)

        owner = db.scalar(select(RoleRecord).where(RoleRecord.name == "OWNER"))
        super_admin = db.scalar(select(RoleRecord).where(RoleRecord.name == "SUPER_ADMIN"))
        admin = db.scalar(select(RoleRecord).where(RoleRecord.name == "ADMIN"))
        user = db.scalar(select(RoleRecord).where(RoleRecord.name == "USER"))

        assert owner is not None
        assert super_admin is not None
        assert admin is not None
        assert user is not None

        assert DOMAIN_PERMISSIONS.issubset(set(permission_codes_for_role(owner)))
        assert DOMAIN_PERMISSIONS.issubset(set(permission_codes_for_role(super_admin)))
        assert DOMAIN_PERMISSIONS.issubset(set(permission_codes_for_role(admin)))

        user_permissions = set(permission_codes_for_role(user))
        assert "domain.account_intelligence.view" in user_permissions
        assert "domain.account_heatmap.view" not in user_permissions
        assert "domain.non_human_identity.view" not in user_permissions
