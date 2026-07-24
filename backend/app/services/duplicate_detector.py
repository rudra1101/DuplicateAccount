from rapidfuzz import fuzz


def calculate_confidence(account1, account2):

    score = 0

    # Email Match (40)
    if account1["email"].lower() == account2["email"].lower():
        score += 40

    # Employee ID (30)
    if account1["employee_id"] == account2["employee_id"]:
        score += 30

    # Username (15)
    username_score = fuzz.ratio(
        account1["username"],
        account2["username"]
    )
    score += (username_score / 100) * 15

    # First Name (10)
    if account1["first_name"].lower() == account2["first_name"].lower():
        score += 10

    # Last Name (5)
    if account1["last_name"].lower() == account2["last_name"].lower():
        score += 5

    return round(score, 2)


def detect_duplicates(accounts):

    duplicates = []

    for i in range(len(accounts)):
        for j in range(i + 1, len(accounts)):

            confidence = calculate_confidence(
                accounts[i],
                accounts[j]
            )

            if confidence >= 80:

                duplicates.append({
                    "account1": accounts[i],
                    "account2": accounts[j],
                    "confidence": confidence
                })

    return duplicates