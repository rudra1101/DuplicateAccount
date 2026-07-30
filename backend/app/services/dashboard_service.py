from app.store import memory_store


def get_dashboard_summary():

    duplicate_group_count = sum(
        len(groups)
        for groups in memory_store.duplicate_groups.values()
    )

    duplicate_account_count = sum(
        group["duplicates"]
        for groups in memory_store.duplicate_groups.values()
        for group in groups
    )

    high_confidence = sum(
        1
        for groups in memory_store.duplicate_groups.values()
        for group in groups
        if group["highestConfidence"] >= 95
    )

    return {
        "accountsScanned": len(memory_store.accounts),
        "applications": len(memory_store.duplicate_groups),
        "duplicateGroups": duplicate_group_count,
        "duplicateAccounts": duplicate_account_count,
        "highConfidence": high_confidence,
        "lastScan": memory_store.last_scan,
    }