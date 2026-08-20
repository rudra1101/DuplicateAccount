import getpass
from app.auth.security import hash_password
from app.database.session import SessionLocal
from app.db_models.user import UserRecord

username = input("Admin username: ").strip()
email = input("Admin email: ").strip()
full_name = input("Admin full name: ").strip()
password = getpass.getpass("Admin password (12+ chars): ")

if len(password) < 12:
    raise SystemExit("Password must be at least 12 characters.")

db = SessionLocal()
try:
    db.add(UserRecord(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role="ADMIN",
        is_active=True,
    ))
    db.commit()
    print(f"Created ADMIN user: {username}")
finally:
    db.close()
