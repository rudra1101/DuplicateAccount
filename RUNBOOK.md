# IdentityAI Production Operations Runbook

This runbook is for operating the IdentityAI application after deployment. It assumes the Phase 13 health, readiness, structured logging, request IDs, Prometheus metrics, and Docker deployment controls are enabled.

## 1. Service map

```text
Browser
  |
  v
Frontend Nginx :8080
  |
  +--> /api/* --> FastAPI backend :8000
                  |
                  +--> PostgreSQL :5432
                  |
                  +--> Scheduler / integration jobs
                  |
                  +--> /metrics --> Prometheus
```

Only the frontend should normally be exposed publicly. Backend and PostgreSQL stay on the internal container network.

## 2. Primary health checks

Application liveness:

```text
/api/health/live
```

Use this to answer: "Is the backend process alive?"

Application readiness:

```text
/api/health/ready
```

Use this to answer: "Can this backend instance serve traffic and reach its critical dependencies?"

Operations UI:

```text
Operations -> System Status
```

Use this for database pool state, scheduler state, integration counts, execution counts, scan/account volume, duplicates, and pending remediation.

## 3. First response to an incident

1. Check `/api/health/live`.
2. Check `/api/health/ready`.
3. Open Operations -> System Status.
4. Check recent backend logs.
5. Capture the `X-Request-ID` from the failing browser/API request when available.
6. Search structured logs for the same request ID.
7. Check Prometheus alerts and the relevant metric trend.
8. Do not restart or roll back until the failing dependency is identified when possible.

## 4. Docker status and logs

Container status:

```powershell
docker compose --env-file backend/.env ps
```

Backend logs:

```powershell
docker compose --env-file backend/.env logs --tail 200 backend
```

Follow backend logs:

```powershell
docker compose --env-file backend/.env logs -f backend
```

Database logs:

```powershell
docker compose --env-file backend/.env logs --tail 200 postgres
```

Frontend logs:

```powershell
docker compose --env-file backend/.env logs --tail 200 frontend
```

## 5. Request-ID troubleshooting

Every HTTP response should include:

```text
X-Request-ID: <uuid-or-client-supplied-id>
```

Backend structured logs include the same value as `request_id`.

When a user reports a 500 error, ask for the request ID from the response if available, then search the application logs for that identifier. This is the preferred way to correlate a browser error with the exact backend request and exception.

## 6. Alert response

### IdentityAIBackendDown — critical

Meaning: Prometheus cannot scrape the backend for at least 2 minutes.

Actions:

1. Check Docker/container status.
2. Check backend startup logs.
3. Check whether Alembic migration failed.
4. Check PostgreSQL health.
5. Check `/api/health/live` from inside the network if necessary.
6. Restart only after capturing the startup/error logs.

### IdentityAIHighServerErrorRate — warning

Meaning: more than 5% of requests have returned HTTP 5xx for 10 minutes.

Actions:

1. Identify which route has the highest 5xx rate in Prometheus.
2. Use request IDs from recent failures to inspect logs.
3. Check database and scheduler health.
4. Check whether a recent deployment changed the failing path.
5. Roll back the application image if the failure started immediately after deployment and no data/schema rollback is required.

### IdentityAIHighP95Latency — warning

Meaning: p95 request latency is above 2 seconds for 10 minutes.

Actions:

1. Check database pool utilization.
2. Check PostgreSQL CPU/locks/slow queries in the target environment.
3. Check whether integration or report workloads are saturating the backend.
4. Identify slow route templates from request-duration metrics/logs.
5. Scale or tune only after identifying the bottleneck.

### IdentityAISchedulerStopped — critical

Meaning: the application scheduler has reported a stopped state for 5 minutes.

Actions:

1. Check backend process health.
2. Check backend startup/shutdown logs.
3. Review Operations -> System Status -> Scheduler.
4. Confirm registered jobs and next-run times.
5. Restart the backend if the scheduler failed to initialize and the database is healthy.
6. Verify missed jobs before manually triggering/retrying work.

### IdentityAIDatabasePoolNearCapacity — warning

Meaning: more than 80% of the configured SQLAlchemy connection pool has remained checked out for 10 minutes.

Actions:

1. Check request latency and 5xx rate.
2. Check PostgreSQL active sessions and long-running queries.
3. Look for endpoints/jobs holding transactions too long.
4. Confirm `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` match expected concurrency.
5. Do not simply increase the pool until PostgreSQL capacity and transaction behavior are understood.

## 7. Database / migration failure

If the backend fails during `alembic upgrade head`:

1. Do not start the API with an unknown schema state.
2. Capture the Alembic error and current revision.
3. Inspect:

```powershell
docker compose --env-file backend/.env run --rm backend python -m alembic current
```

4. Inspect migration history:

```powershell
docker compose --env-file backend/.env run --rm backend python -m alembic history
```

5. Fix forward whenever possible.
6. Never run a destructive Alembic downgrade in production without a verified backup and migration-specific rollback plan.

## 8. Restart procedure

Restart backend only:

```powershell
docker compose --env-file backend/.env restart backend
```

After restart verify:

1. backend container is healthy;
2. `/api/health/live` is 200;
3. `/api/health/ready` is 200;
4. scheduler is running;
5. no migration/startup errors are present.

## 9. Deployment rollback

Application rollback should use the previously known-good container image or commit.

Before rollback determine whether the failed release introduced a database migration.

- If there was no schema change, application rollback is normally straightforward.
- If a migration was applied, confirm the previous application version is compatible with the new schema before rolling back.
- Prefer backward-compatible migrations and forward fixes.
- Database rollback requires an explicit backup/restore or migration-specific plan; do not assume application rollback also rolls back data.

## 10. PostgreSQL backup expectation

Before a production release containing schema changes, create and verify a PostgreSQL backup using the platform-approved backup method. A backup is only useful if restore has been tested.

At minimum retain:

- database backup timestamp;
- application release/commit SHA;
- Alembic revision;
- restoration procedure and target location.

## 11. Monitoring

Start the optional local Prometheus profile with:

```powershell
docker compose --env-file backend/.env --profile monitoring up --build -d
```

Prometheus UI:

```text
http://localhost:9090
```

Useful metrics include:

```text
identityai_http_requests_total
identityai_http_request_duration_seconds_bucket
identityai_http_requests_in_progress
identityai_database_pool_size
identityai_database_pool_checked_out
identityai_scheduler_running
identityai_scheduler_jobs
identityai_integrations
identityai_job_executions
identityai_accounts_total_current
identityai_duplicate_groups_total_current
identityai_duplicate_candidates_total_current
identityai_pending_remediation_total_current
```

In a real production environment, Prometheus and alert delivery should normally be placed behind the organization's monitoring/access controls rather than exposing port 9090 publicly.

## 12. Post-incident checklist

After recovery:

1. Record incident start/end time.
2. Record affected feature/routes.
3. Save relevant request IDs and logs.
4. Record the root cause.
5. Record the recovery action.
6. Add a test, alert, dashboard, or runbook improvement that would detect or prevent the same failure earlier next time.
