from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from app.ai.blocking.email_blocker import (
    build_email_keys,
)
from app.ai.blocking.employee_blocker import (
    build_employee_keys,
)
from app.ai.blocking.name_blocker import (
    build_name_keys,
)
from app.ai.blocking.normalizer import (
    get_account_value,
    get_source_key,
    normalize_text,
)
from app.ai.blocking.username_blocker import (
    build_username_keys,
)


@dataclass(slots=True)
class BlockingCandidate:
    account_1_index: int
    account_2_index: int
    account_1: Any
    account_2: Any
    shared_block_keys: list[str]
    blocking_score: float
    reasons: list[str] = field(
        default_factory=list
    )


class BlockingCandidateGenerator:
    def __init__(
        self,
        *,
        max_block_size: int = 100,
        max_candidates_per_account: int = 25,
        minimum_blocking_score: float = 2.0,
        cross_application_only: bool = False,
    ) -> None:
        self.max_block_size = max_block_size
        self.max_candidates_per_account = (
            max_candidates_per_account
        )
        self.minimum_blocking_score = (
            minimum_blocking_score
        )
        self.cross_application_only = (
            cross_application_only
        )

    def build_keys(
        self,
        account: Any,
    ) -> set[str]:
        keys: set[str] = set()

        keys.update(
            build_employee_keys(
                get_account_value(
                    account,
                    "employee_id",
                )
            )
        )

        keys.update(
            build_email_keys(
                get_account_value(
                    account,
                    "email",
                )
            )
        )

        keys.update(
            build_username_keys(
                get_account_value(
                    account,
                    "username",
                )
            )
        )

        keys.update(
            build_name_keys(
                display_name=get_account_value(
                    account,
                    "display_name",
                ),
                first_name=get_account_value(
                    account,
                    "first_name",
                ),
                last_name=get_account_value(
                    account,
                    "last_name",
                ),
            )
        )

        return keys

    @staticmethod
    def weight(key: str) -> float:
        weights = (
            ("employee:exact:", 10.0),
            ("email:exact:", 8.0),
            ("username:exact:", 6.0),
            ("name:exact:", 5.0),
            ("name:first-last:", 4.5),
            ("email:local:", 4.0),
            ("username:prefix6:", 2.0),
            (
                "name:first-initial-last:",
                2.0,
            ),
            ("name:prefix6:", 1.5),
            ("username:suffix4:", 1.0),
            ("email:local-prefix6:", 1.0),
        )

        for prefix, value in weights:
            if key.startswith(prefix):
                return value

        return 0.0

    @staticmethod
    def reason(key: str) -> str:
        labels = (
            (
                "employee:exact:",
                "Exact employee ID",
            ),
            (
                "email:exact:",
                "Exact email",
            ),
            (
                "email:local:",
                "Matching email local part",
            ),
            (
                "username:exact:",
                "Exact normalized username",
            ),
            (
                "username:prefix6:",
                "Matching username prefix",
            ),
            (
                "username:suffix4:",
                "Matching username suffix",
            ),
            (
                "name:exact:",
                "Exact normalized name",
            ),
            (
                "name:first-last:",
                "Matching first and last name",
            ),
            (
                "name:first-initial-last:",
                "Matching first initial and last name",
            ),
            (
                "name:prefix6:",
                "Matching name prefix",
            ),
        )

        for prefix, label in labels:
            if key.startswith(prefix):
                return label

        return "Shared blocking key"

    def _allowed(
        self,
        account_1: Any,
        account_2: Any,
        index_1: int,
        index_2: int,
    ) -> bool:
        if (
            get_source_key(
                account_1,
                index_1,
            )
            == get_source_key(
                account_2,
                index_2,
            )
        ):
            return False

        if not self.cross_application_only:
            return True

        return (
            normalize_text(
                get_account_value(
                    account_1,
                    "application",
                )
            )
            != normalize_text(
                get_account_value(
                    account_2,
                    "application",
                )
            )
        )

    def generate(
        self,
        accounts: list[Any],
    ) -> list[BlockingCandidate]:
        if len(accounts) < 2:
            return []

        block_index: dict[
            str,
            list[int],
        ] = defaultdict(list)

        for index, account in enumerate(
            accounts
        ):
            for key in self.build_keys(
                account
            ):
                block_index[key].append(
                    index
                )

        pair_keys: dict[
            tuple[int, int],
            set[str],
        ] = defaultdict(set)

        for key, indexes in (
            block_index.items()
        ):
            if (
                len(indexes) < 2
                or len(indexes)
                > self.max_block_size
                or self.weight(key) <= 0
            ):
                continue

            for index_1, index_2 in (
                combinations(indexes, 2)
            ):
                if self._allowed(
                    accounts[index_1],
                    accounts[index_2],
                    index_1,
                    index_2,
                ):
                    pair_keys[
                        (index_1, index_2)
                    ].add(key)

        candidates: list[
            BlockingCandidate
        ] = []

        for (
            index_1,
            index_2,
        ), keys in pair_keys.items():
            score = sum(
                self.weight(key)
                for key in keys
            )

            if (
                score
                < self.minimum_blocking_score
            ):
                continue

            sorted_keys = sorted(
                keys,
                key=lambda key: (
                    -self.weight(key),
                    key,
                ),
            )

            candidates.append(
                BlockingCandidate(
                    account_1_index=index_1,
                    account_2_index=index_2,
                    account_1=accounts[
                        index_1
                    ],
                    account_2=accounts[
                        index_2
                    ],
                    shared_block_keys=(
                        sorted_keys
                    ),
                    blocking_score=round(
                        score,
                        2,
                    ),
                    reasons=[
                        self.reason(key)
                        for key in sorted_keys
                    ],
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.blocking_score,
                candidate.account_1_index,
                candidate.account_2_index,
            )
        )

        selected: list[
            BlockingCandidate
        ] = []

        counts: dict[
            int,
            int,
        ] = defaultdict(int)

        for candidate in candidates:
            left = (
                candidate.account_1_index
            )
            right = (
                candidate.account_2_index
            )

            if (
                counts[left]
                >= self.max_candidates_per_account
                or counts[right]
                >= self.max_candidates_per_account
            ):
                continue

            selected.append(candidate)
            counts[left] += 1
            counts[right] += 1

        return selected


blocking_candidate_generator = (
    BlockingCandidateGenerator()
)
