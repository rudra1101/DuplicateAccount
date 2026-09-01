from types import SimpleNamespace

from app.services.review_visibility_service import _candidate_is_visible


APPLICATION = "Active Directory"
PRIMARY = {"id": "100", "username": "john.smith"}
CANDIDATE = {
    "reviewDecision": None,
    "account": {"id": "200", "username": "jsmith"},
}
PAIR = ("active directory:100", "active directory:200")


def _visible(*, remediation_status=None, durable_decision=None, current_decision=None):
    candidate = {**CANDIDATE, "reviewDecision": current_decision}
    remediation = (
        {PAIR: SimpleNamespace(status=remediation_status)}
        if remediation_status
        else {}
    )
    feedback = (
        {(APPLICATION, *PAIR): durable_decision}
        if durable_decision
        else {}
    )
    return _candidate_is_visible(
        application=APPLICATION,
        primary_account=PRIMARY,
        candidate=candidate,
        remediation_by_pair=remediation,
        durable_feedback=feedback,
    )


def test_confirmed_duplicate_pending_remediation_is_hidden():
    assert _visible(remediation_status="PENDING_ACTION", durable_decision="DUPLICATE") is False


def test_open_or_completed_remediation_stays_hidden():
    assert _visible(remediation_status="TICKET_OPEN", durable_decision="DUPLICATE") is False
    assert _visible(remediation_status="ACTIONED", durable_decision="DUPLICATE") is False


def test_manual_ignore_returns_pair_to_review_after_durable_duplicate_is_cleared():
    assert _visible(remediation_status="IGNORED") is True


def test_not_duplicate_remains_hidden_even_when_remediation_record_is_ignored():
    assert _visible(remediation_status="IGNORED", durable_decision="NOT_DUPLICATE") is False


def test_uncertain_pair_remains_reviewable():
    assert _visible(remediation_status="IGNORED", current_decision="UNCERTAIN") is True


def test_previous_durable_decision_suppresses_same_pair_on_later_scan():
    assert _visible(durable_decision="DUPLICATE") is False
    assert _visible(durable_decision="NOT_DUPLICATE") is False
