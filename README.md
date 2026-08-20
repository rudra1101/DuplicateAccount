# IdentityAI Auth + RBAC

Roles: `ADMIN` and `USER`.

ADMIN can create USER/ADMIN accounts, create/edit/delete/test integrations, run integrations, and manage schedules.

USER can sign in, view integrations, run integrations, manage schedules, and view history. USER cannot see or navigate to admin-only pages.

## Backend dependencies
Add to `backend/requirements.txt`:
```text
PyJWT>=2.10,<3
argon2-cffi>=23,<26
email-validator>=2,<3
```

## Environment
Add locally to `backend/.env`:
```env
AUTH_SECRET_KEY=<strong-random-secret>
AUTH_ACCESS_TOKEN_MINUTES=480
AUTH_COOKIE_SECURE=false
```

Generate a secret:
```powershell
..\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

## First admin
```powershell
$env:PYTHONPATH="."
..\venv\Scripts\python.exe scripts\create_admin.py
```

## Required backend RBAC
`ADMIN` only:
- create integration
- edit/update integration
- delete integration
- test integration
- user management

`ADMIN` + `USER`:
- list/view integrations
- run integration
- create/update/enable/disable/delete schedules
- view execution history

## Required frontend RBAC
ADMIN-only routes:
- `/admin`
- `/users`
- `/integrations/new`
- `/integrations/:integrationId/edit`

For USER:
- hide Admin
- hide User Management
- hide Add Integration
- hide Edit/Delete/Test
- keep Run Now / Schedule / History

Backend authorization must still return 403 if USER directly calls an ADMIN-only endpoint.
