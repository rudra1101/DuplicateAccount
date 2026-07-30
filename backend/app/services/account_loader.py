import json
from pathlib import Path

from app.models.account import Account


DATA_FILE = (
    Path(__file__).parent.parent
    / "data"
    / "sample_accounts.json"
)


def load_accounts():

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    return [Account(**account) for account in data]