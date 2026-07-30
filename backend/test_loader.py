from app.services.account_loader import load_accounts

accounts = load_accounts()

for account in accounts:
    print(account.username)