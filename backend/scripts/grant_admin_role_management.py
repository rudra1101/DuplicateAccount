from sqlalchemy import select

from app.database.session import SessionLocal
from app.db_models.permission import PermissionRecord
from app.db_models.role import RoleRecord


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(RoleRecord).where(RoleRecord.name == "ADMIN"))
        if admin is None:
            raise SystemExit("ADMIN role not found. Start the backend once so RBAC is seeded.")

        permissions = db.scalars(select(PermissionRecord)).all()
        admin.permissions = list(permissions)
        admin.description = (
            "Application administrator with user, integration, role, "
            "and permission management capabilities."
        )
        db.commit()

        print("ADMIN role now has all configurable application permissions.")
        print("OWNER remains protected and cannot be modified or deleted.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
