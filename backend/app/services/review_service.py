from app.store import memory_store


def get_review_summary():

    summary = []

    applications = {}

    for account in memory_store.accounts:

        if isinstance(account, dict):
            app = account["application"]
        else:
            app = account.application

        applications[app] = applications.get(app, 0) + 1

    for app_name, groups in memory_store.duplicate_groups.items():

        duplicate_accounts = sum(
            group["duplicates"]
            for group in groups
        )

        summary.append(
            {
                "application": app_name,
                "totalAccounts": applications.get(app_name, 0),
                "duplicateGroups": len(groups),
                "duplicateAccounts": duplicate_accounts,
                "highConfidence": sum(
                    1
                    for group in groups
                    if group["highestConfidence"] >= 95
                ),
                "lastScan": (
                    memory_store.last_scan.strftime("%Y-%m-%d %H:%M:%S")
                    if memory_store.last_scan
                    else None
                ),
            }
        )

    return summary


def get_duplicate_groups(application: str):

    return memory_store.duplicate_groups.get(application, [])


def get_duplicate_group_details(group_id: int):

    return memory_store.duplicate_details.get(group_id)


def get_scan_status():

    return {
        "accounts": len(memory_store.accounts),
        "applications": len(memory_store.duplicate_groups),
        "lastScan": memory_store.last_scan,
    }