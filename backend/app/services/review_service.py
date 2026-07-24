from app.ai.duplicate_engine import detect_duplicates
from app.schemas.account import Account

duplicates_cache = []


def scan_accounts(accounts: list[Account]):
    global duplicates_cache

    duplicates_cache = detect_duplicates(accounts)

    return duplicates_cache


def get_duplicates():
    return duplicates_cache