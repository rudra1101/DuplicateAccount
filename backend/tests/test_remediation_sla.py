from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.remediation_sla_service import calculate_sla_state


def _record(*, due_at, status="PENDING_ACTION", escalated_at=None):
    return SimpleNamespace(
        sla_due_at=due_at,
        status=status,
        sla_escalated_at=escalated_at,
    )


def test_sla_on_track_before_warning_window():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    record = _record(due_at=now + timedelta(hours=48))
    assert calculate_sla_state(record, warning_hours=24, enabled=True, now=now) == "ON_TRACK"


def test_sla_warning_inside_warning_window():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    record = _record(due_at=now + timedelta(hours=12))
    assert calculate_sla_state(record, warning_hours=24, enabled=True, now=now) == "WARNING"


def test_sla_overdue_after_deadline():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    record = _record(due_at=now - timedelta(minutes=1))
    assert calculate_sla_state(record, warning_hours=24, enabled=True, now=now) == "OVERDUE"


def test_sla_escalated_takes_precedence():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    record = _record(
        due_at=now - timedelta(hours=2),
        escalated_at=now - timedelta(hours=1),
    )
    assert calculate_sla_state(record, warning_hours=24, enabled=True, now=now) == "ESCALATED"


def test_completed_or_disabled_sla_is_not_tracked():
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    completed = _record(due_at=now - timedelta(hours=1), status="ACTIONED")
    active = _record(due_at=now - timedelta(hours=1))
    assert calculate_sla_state(completed, warning_hours=24, enabled=True, now=now) == "NONE"
    assert calculate_sla_state(active, warning_hours=24, enabled=False, now=now) == "NONE"
