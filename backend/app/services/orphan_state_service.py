from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models.account import AccountRecord
from app.db_models.orphan_finding import OrphanFindingRecord
from app.db_models.orphan_state import OrphanStateRecord
from app.db_models.scan import ScanRecord
from app.db_models.source_account import SourceAccountRecord


def _key(application: str | None, native_identity: str | None) -> tuple[str, str] | None:
    app = str(application or "").strip().lower()
    native = str(native_identity or "").strip().lower()
    if not app or not native:
        return None
    return app, native


def reconcile_orphan_states(
    db: Session,
    *,
    scan_id: int,
    findings: list[OrphanFindingRecord],
) -> dict[str, int]:
    """Reconcile durable orphan state from one completed FULL account scan.

    Scan-bound orphan_findings remain historical evidence. orphan_states represents
    the current state keyed by the persistent source_accounts row.
    """
    scan = db.get(ScanRecord, scan_id)
    if scan is None or scan.integration_id is None:
        raise ValueError("Scan is not linked to an integration.")

    integration_id = scan.integration_id
    now = datetime.now(UTC)

    accounts = list(
        db.scalars(select(AccountRecord).where(AccountRecord.scan_id == scan_id)).all()
    )
    accounts_by_id = {account.id: account for account in accounts}

    source_accounts = list(
        db.scalars(
            select(SourceAccountRecord).where(
                SourceAccountRecord.integration_id == integration_id
            )
        ).all()
    )
    source_by_key = {
        key: source
        for source in source_accounts
        if (key := _key(source.application, source.native_identity)) is not None
    }

    existing = list(
        db.scalars(
            select(OrphanStateRecord).where(
                OrphanStateRecord.integration_id == integration_id
            )
        ).all()
    )
    existing_by_source_id = {state.source_account_id: state for state in existing}

    seen_source_ids: set[int] = set()
    created = updated = 0

    for finding in findings:
        account = accounts_by_id.get(finding.account_id)
        if account is None:
            continue
        source = source_by_key.get(_key(account.application, account.source_account_id))
        if source is None:
            continue

        seen_source_ids.add(source.id)
        state = existing_by_source_id.get(source.id)
        if state is None:
            state = OrphanStateRecord(
                integration_id=integration_id,
                source_account_id=source.id,
                orphan_type=finding.orphan_type,
                correlation_method=finding.correlation_method,
                matched_identity_id=finding.matched_identity_id,
                evidence=finding.evidence or {},
                status="OPEN",
                active=True,
                first_detected_at=now,
                last_detected_at=now,
                last_scan_id=scan_id,
                created_at=now,
                updated_at=now,
            )
            db.add(state)
            existing_by_source_id[source.id] = state
            created += 1
        else:
            state.orphan_type = finding.orphan_type
            state.correlation_method = finding.correlation_method
            state.matched_identity_id = finding.matched_identity_id
            state.evidence = finding.evidence or {}
            state.status = "OPEN"
            state.active = True
            state.last_detected_at = now
            state.last_scan_id = scan_id
            state.updated_at = now
            updated += 1

    resolved = 0
    for state in existing:
        if state.source_account_id in seen_source_ids:
            continue
        if state.active:
            state.active = False
            state.status = "RESOLVED"
            state.updated_at = now
            resolved += 1

    db.commit()
    return {"created": created, "updated": updated, "resolved": resolved, "active": len(seen_source_ids)}
