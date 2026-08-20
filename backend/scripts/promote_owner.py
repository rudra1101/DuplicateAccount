from sqlalchemy import select

from app.database.session import SessionLocal
from app.db_models.user import UserRecord


username = input("Existing username to promote to OWNER: ").strip()

with SessionLocal() as db:
    user = db.scalar(select(UserRecord).where(UserRecord.username == username))
    if user is None:
        raise SystemExit("User not found.")

    user.role = "OWNER"
    db.commit()
    print(f"Promoted {username} to OWNER.")
