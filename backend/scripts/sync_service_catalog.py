from app.database.session import SessionLocal
from app.services.rbac_service import seed_rbac


def main() -> None:
    with SessionLocal() as db:
        seed_rbac(db)
    print("Service catalog synchronized successfully.")


if __name__ == "__main__":
    main()
