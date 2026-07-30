from app.store.memory_store import (
    accounts,
    duplicate_groups,
    duplicate_details,
    last_scan,
)


def get_review_summary():

    summary = []

    for application, groups in duplicate_groups.items():

        summary.append(
            {
                "application": application,
                "duplicateGroups": len(groups),
                "highConfidence": sum(
                    1
                    for group in groups
                    if group["highestConfidence"] >= 95
                ),
            }
        )

    return summary


def get_duplicate_groups(application):

    return duplicate_groups.get(application, [])


def get_duplicate_group_details(group_id):

    return duplicate_details.get(group_id)


def get_scan_status():

    return {
        "accounts": len(accounts),
        "applications": len(duplicate_groups),
        "lastScan": last_scan,
    }