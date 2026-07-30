from collections import defaultdict
from rapidfuzz import fuzz

from app.models.account import Account


def calculate_confidence(account1: Account, account2: Account):

    score = 0

    matched = []
    different = []

    # Employee ID (40)
    if account1.employeeId == account2.employeeId:
        score += 40
        matched.append("Employee ID")
    else:
        different.append("Employee ID")

    # Email (30)
    if account1.email.lower() == account2.email.lower():
        score += 30
        matched.append("Email")
    else:
        different.append("Email")

    # Display Name (15)
    similarity = fuzz.ratio(
        account1.displayName,
        account2.displayName,
    )

    if similarity > 90:
        score += 15
        matched.append("Display Name")
    else:
        different.append("Display Name")

    # Department (5)
    if account1.department == account2.department:
        score += 5
        matched.append("Department")
    else:
        different.append("Department")

    # Manager (5)
    if account1.manager == account2.manager:
        score += 5
        matched.append("Manager")
    else:
        different.append("Manager")

    # Username Similarity (5)
    similarity = fuzz.ratio(
        account1.username,
        account2.username,
    )

    if similarity > 70:
        score += 5
        matched.append("Username")
    else:
        different.append("Username")

    return score, matched, different

def detect_duplicate_groups(accounts):

    grouped = defaultdict(list)

    # Group by Application
    applications = defaultdict(list)

    for account in accounts:
        applications[account.application].append(account)

    group_id = 1

    results = defaultdict(list)

    details = {}

    for application, app_accounts in applications.items():

        visited = set()

        for account in app_accounts:

            if account.username in visited:
                continue

            duplicates = []

            for other in app_accounts:

                if account.username == other.username:
                    continue

                score, matched, different = calculate_confidence(
                    account,
                    other,
                )

                if score >= 80:

                    duplicates.append(
                        {
                            "id": len(duplicates) + 1,
                            "confidence": score,
                            "recommendation": (
                                "MERGE"
                                if score >= 95
                                else "REVIEW"
                            ),
                            "matchedAttributes": matched,
                            "differentAttributes": different,
                            "account": other.model_dump(),
                        }
                    )

                    visited.add(other.username)

            if duplicates:

                visited.add(account.username)

                results[application].append(
                    {
                        "groupId": group_id,
                        "primaryAccount": account.username,
                        "duplicates": len(duplicates),
                        "highestConfidence": max(
                            d["confidence"]
                            for d in duplicates
                        ),
                    }
                )

                details[group_id] = {
                    "primaryAccount": account.model_dump(),
                    "duplicates": duplicates,
                }

                group_id += 1

    return results, details