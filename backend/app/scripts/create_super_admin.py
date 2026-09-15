from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database.session import SessionLocal
from app.db_models.role import RoleRecord
from app.db_models.user import UserRecord
from app.services.rbac_service import seed_rbac

SUPER_ADMIN_ROLE = "SUPER_ADMIN"
MIN_PASSWORD_LENGTH = 12


def create_super_admin(
    db: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
) -> UserRecord:
    username = username.strip()
    email = email.strip()
    full_name = full_name.strip()

    if not username:
        raise ValueError("Username is required.")
    if not email:
        raise ValueError("Email is required.")
    if not full_name:
        raise ValueError("Full name is required.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    # Ensure system roles and permissions are present before creating the account.
    seed_rbac(db)

    role = db.scalar(select(RoleRecord).where(RoleRecord.name == SUPER_ADMIN_ROLE))
    if role is None:
        raise RuntimeError("SUPER_ADMIN role was not seeded successfully.")

    existing = db.scalar(
        select(UserRecord).where(
            or_(UserRecord.username == username, UserRecord.email == email)
        )
    )
    if existing is not None:
        if existing.username == username:
            raise ValueError(f"A user with username '{username}' already exists.")
        raise ValueError(f"A user with email '{email}' already exists.")

    user = UserRecord(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role=SUPER_ADMIN_ROLE,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _password_from_prompt() -> str:
    env_password = os.getenv("IDENTITYAI_BOOTSTRAP_PASSWORD", "")
    if env_password:
        return env_password

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the initial IdentityAI SUPER_ADMIN account.",
    )
    parser.add_argument("--username", default="superadmin")
    parser.add_argument("--email", default="superadmin@identityai.local")
    parser.add_argument("--full-name", default="Super Admin")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        password = _password_from_prompt()
        with SessionLocal() as db:
            user = create_super_admin(
                db,
                username=args.username,
                email=args.email,
                full_name=args.full_name,
                password=password,
            )
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"SUPER_ADMIN created successfully: "
        f"id={user.id}, username={user.username}, email={user.email}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
