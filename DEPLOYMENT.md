# IdentityAI Docker Deployment

This repository uses the existing `backend/.env` as the single local environment file. Do not create or commit a second environment file.

## 1. Add Docker database variables to `backend/.env`

Keep your existing settings and add the following section if the variables are not already present:

```env
# =========================
# DOCKER POSTGRESQL
# =========================
POSTGRES_DB=identityai
POSTGRES_USER=identityai
POSTGRES_PASSWORD=replace-with-a-strong-local-password

# =========================
# APPLICATION RUNTIME
# =========================
APP_ENV=development
ALLOWED_HOSTS=localhost,127.0.0.1,backend,testserver
CORS_ORIGINS=
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
SECURITY_HEADERS_ENABLED=true
```

Inside Docker, Compose passes the PostgreSQL host, user, database, and password as separate environment values. The backend builds the SQLAlchemy connection URL safely, so special password characters do not require manual URL encoding. Your existing local `DATABASE_URL` can remain unchanged for non-Docker development.

## 2. Start the stack

From the repository root:

```powershell
docker compose --env-file backend/.env up --build -d
```

The startup order is:

1. PostgreSQL starts and passes `pg_isready`.
2. Backend waits for the database.
3. Backend runs `alembic upgrade head`.
4. FastAPI starts and must pass `/api/health/ready`.
5. Frontend Nginx starts and proxies `/api` to the backend.

Open the application at:

```text
http://localhost:8080
```

The backend and PostgreSQL services are intentionally not published to host ports by Compose.

## 3. Check service health

```powershell
docker compose --env-file backend/.env ps
```

Browser-accessible checks through Nginx:

```text
http://localhost:8080/api/health/live
http://localhost:8080/api/health/ready
```

Backend logs:

```powershell
docker compose --env-file backend/.env logs -f backend
```

PostgreSQL logs:

```powershell
docker compose --env-file backend/.env logs -f postgres
```

## 4. Stop the stack

```powershell
docker compose --env-file backend/.env down
```

The PostgreSQL Docker volume is retained.

To intentionally remove the Docker database as well:

```powershell
docker compose --env-file backend/.env down -v
```

Do not use `-v` if the Docker PostgreSQL data must be retained.

## 5. Important data note

The Docker PostgreSQL volume is a separate database from PostgreSQL installed directly on your Windows machine. Starting the Docker stack does not copy your existing local IdentityAI PostgreSQL data into the container database.

For initial container testing, an empty migrated schema is expected. Data migration/import should be handled explicitly before using the Docker database as the authoritative environment.

## 6. Actual production settings

For a real HTTPS deployment, update the same `backend/.env` with production-safe values before deployment:

```env
APP_ENV=production
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
AUTH_SECRET_KEY=use-a-long-random-secret-at-least-32-characters
ALLOWED_HOSTS=identity.example.com
CORS_ORIGINS=
```

A same-origin deployment does not require CORS. If a separate frontend origin is used, set `CORS_ORIGINS` to the explicit HTTPS frontend origin.

Never commit `backend/.env` or real credentials.
