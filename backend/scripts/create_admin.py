import getpass

from sqlalchemy import or_, select

from app.auth.security import hash_password
from app.database.session import SessionLocal
from app.db_models.user import UserRecord


def main():
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password (12+ chars): ")
    confirmation = getpass.getpass("Confirm password: ")

    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    db = SessionLocal()
    try:
        existing = db.scalar(
            select(UserRecord).where(
                or_(UserRecord.username == username, UserRecord.email == email)
            )
        )
        if existing is not None:
            raise SystemExit("Username or email already exists.")

        user = UserRecord(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="ADMIN",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created ADMIN user: {username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
