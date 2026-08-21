import app.db_models  # noqa: F401
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.services.rbac_service import seed_rbac


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_rbac(db)
    print("Service catalog synchronized successfully.")


if __name__ == "__main__":
    main()
