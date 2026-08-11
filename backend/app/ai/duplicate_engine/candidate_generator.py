from collections import defaultdict
from itertools import combinations

from app.ai.duplicate_engine.types import (
    NormalizedAccount,
)


AccountPair = tuple[
    NormalizedAccount,
    NormalizedAccount,
]


def build_blocking_keys(
    account: NormalizedAccount,
) -> set[str]:
    keys: set[str] = set()

    if account.employee_id:
        keys.add(
            f"employee:{account.employee_id}"
        )

    if account.email:
        keys.add(
            f"email:{account.email}"
        )

    if account.email_local_part:
        keys.add(
            "email-local:"
            f"{account.email_local_part}"
        )

    if account.phone:
        keys.add(
            f"phone:{account.phone}"
        )

    if account.last_name:
        keys.add(
            f"lastname:{account.last_name}"
        )

    if account.first_name:
        keys.add(
            "firstname-prefix:"
            f"{account.first_name[:3]}"
        )

    if account.username:
        compact_username = (
            account.username
            .replace(".", "")
            .replace("_", "")
            .replace("-", "")
        )

        keys.add(
            "username-prefix:"
            f"{compact_username[:4]}"
        )

    if (
        account.department
        and account.last_name
    ):
        keys.add(
            "department-lastname:"
            f"{account.department}:"
            f"{account.last_name}"
        )

    return keys


def pair_key(
    account_1: NormalizedAccount,
    account_2: NormalizedAccount,
) -> tuple[str, str]:
    id_1 = (
        account_1.account_id
        or account_1.username
        or str(id(account_1))
    )

    id_2 = (
        account_2.account_id
        or account_2.username
        or str(id(account_2))
    )

    return tuple(
        sorted(
            (
                id_1,
                id_2,
            )
        )
    )


def generate_candidates(
    accounts: list[NormalizedAccount],
    *,
    cross_application_only: bool = False,
    max_block_size: int = 500,
) -> list[AccountPair]:
    blocks: dict[
        str,
        list[NormalizedAccount],
    ] = defaultdict(list)

    for account in accounts:
        for key in build_blocking_keys(
            account
        ):
            blocks[key].append(account)

    seen_pairs: set[
        tuple[str, str]
    ] = set()

    candidates: list[
        AccountPair
    ] = []

    for block_accounts in blocks.values():
        if len(block_accounts) < 2:
            continue

        if len(block_accounts) > max_block_size:
            continue

        for account_1, account_2 in combinations(
            block_accounts,
            2,
        ):
            if (
                cross_application_only
                and account_1.application
                == account_2.application
            ):
                continue

            key = pair_key(
                account_1,
                account_2,
            )

            if key in seen_pairs:
                continue

            seen_pairs.add(key)

            candidates.append(
                (
                    account_1,
                    account_2,
                )
            )

    return candidates