from pprint import pprint

from app.services.account_loader import load_accounts
from app.services.duplicate_detector import detect_duplicate_groups

accounts = load_accounts()

groups, details = detect_duplicate_groups(accounts)

print("\nAPPLICATION GROUPS\n")
pprint(groups)

print("\nDETAILS\n")
pprint(details)