from app.ai.blocking import BlockingCandidateGenerator
from app.ai.duplicate_engine.normalizer import normalize_account


def _normalized(
    account_id: str,
    username: str,
    email: str,
    display_name: str = "",
):
    return normalize_account(
        {
            "id": account_id,
            "application": "ISC",
            "username": username,
            "email": email,
            "displayName": display_name,
        }
    )


def test_adaptive_fuzzy_expansion_recovers_pair_missed_by_primary_blocks():
    accounts = [
        _normalized(
            "1",
            "rudrashankar",
            "rudrashankar@example.com",
        ),
        _normalized(
            "2",
            "rudraxshankar",
            "rudraxshankar@other.example",
        ),
        _normalized(
            "3",
            "completelydifferent",
            "someoneelse@example.com",
        ),
    ]

    generator = BlockingCandidateGenerator(
        minimum_blocking_score=4.0,
        max_candidates_per_account=10,
    )
    candidates = generator.generate(accounts)

    match = next(
        candidate
        for candidate in candidates
        if {
            candidate.account_1.account_id,
            candidate.account_2.account_id,
        }
        == {"1", "2"}
    )

    assert "Adaptive fuzzy candidate" in match.reasons
    assert match.blocking_score >= 4.0


def test_single_fuzzy_signal_does_not_create_candidate():
    accounts = [
        _normalized(
            "1",
            "rudrashankar",
            "alpha@example.com",
        ),
        _normalized(
            "2",
            "rudraxshankar",
            "totallydifferent@other.example",
        ),
        _normalized(
            "3",
            "thirdperson",
            "third@example.com",
        ),
    ]

    generator = BlockingCandidateGenerator(
        minimum_blocking_score=4.0,
        max_candidates_per_account=10,
    )
    candidates = generator.generate(accounts)

    pairs = {
        frozenset(
            (
                candidate.account_1.account_id,
                candidate.account_2.account_id,
            )
        )
        for candidate in candidates
    }

    assert frozenset(("1", "2")) not in pairs


def test_fuzzy_expansion_preserves_same_source_protection():
    account = _normalized(
        "1",
        "rudrashankar",
        "rudrashankar@example.com",
    )
    accounts = [account, account]

    generator = BlockingCandidateGenerator(
        minimum_blocking_score=4.0,
        max_candidates_per_account=10,
    )

    assert generator.generate(accounts) == []
