from app.schemas.account import Account, DuplicateResult
from app.ai.similarity import similarity


def detect_duplicates(accounts: list[Account]):

    results = []

    for i in range(len(accounts)):
        for j in range(i + 1, len(accounts)):

            a = accounts[i]
            b = accounts[j]

            reasons = []
            score = 0

            name_score = (
                similarity(a.first_name, b.first_name)
                + similarity(a.last_name, b.last_name)
            ) / 2

            if name_score > 85:
                score += 30
                reasons.append("Names are highly similar")

            if a.email.lower() == b.email.lower():
                score += 40
                reasons.append("Email matched")

            if (
                a.employee_id
                and b.employee_id
                and a.employee_id == b.employee_id
            ):
                score += 30
                reasons.append("Employee ID matched")

            if score >= 60:
                results.append(
                    DuplicateResult(
                        account1=a,
                        account2=b,
                        confidence=score,
                        reason=reasons,
                    )
                )

    return results