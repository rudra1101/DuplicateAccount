from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from app.ai.blocking.email_blocker import build_email_keys
from app.ai.blocking.employee_blocker import build_employee_keys
from app.ai.blocking.name_blocker import build_name_keys
from app.ai.blocking.normalizer import (
    get_account_value,
    get_source_key,
    normalize_text,
)
from app.ai.blocking.username_blocker import build_username_keys
from app.ai.duplicate_engine.attribute_profiler import (
    AttributeCategory,
    AttributeProfile,
    dynamic_blocking_profiles,
)
from app.ai.duplicate_engine.normalizer import build_attribute_view
from app.ai.duplicate_engine.similarity import (
    similarity_ratio,
    token_similarity,
    username_similarity,
)


@dataclass(slots=True)
class BlockingCandidate:
    account_1_index: int
    account_2_index: int
    account_1: Any
    account_2: Any
    shared_block_keys: list[str]
    blocking_score: float
    reasons: list[str] = field(default_factory=list)


class BlockingCandidateGenerator:
    """Generate plausible same-application account pairs.

    Primary candidate generation uses deterministic blocking keys. When that
    produces unusually few pairs for a small/medium application, a conservative
    fuzzy-neighbour expansion adds only pairs supported by multiple weak-to-
    strong identity signals. Fuzzy expansion never decides that two accounts
    are duplicates; it only decides which pairs reach the hybrid scorer.
    """

    FUZZY_EXHAUSTIVE_LIMIT = 750
    FUZZY_NEIGHBORS_PER_ACCOUNT = 5

    def __init__(
        self,
        *,
        max_block_size: int = 100,
        max_candidates_per_account: int = 25,
        minimum_blocking_score: float = 2.0,
        cross_application_only: bool = False,
    ) -> None:
        self.max_block_size = max_block_size
        self.max_candidates_per_account = max_candidates_per_account
        self.minimum_blocking_score = minimum_blocking_score
        self.cross_application_only = cross_application_only
        self._dynamic_profiles: dict[str, AttributeProfile] = {}

    @staticmethod
    def _dynamic_key(profile: AttributeProfile, value: Any) -> str | None:
        normalized = normalize_text(value)
        if not normalized or len(normalized) > 300:
            return None
        attribute_name = normalize_text(profile.name).replace(" ", "_")
        return f"dynamic:{attribute_name}:{normalized}"

    @staticmethod
    def _dynamic_weight(profile: AttributeProfile) -> float:
        category_base = {
            AttributeCategory.IDENTIFIER: 7.5,
            AttributeCategory.CONTACT: 7.0,
            AttributeCategory.NAME: 4.5,
            AttributeCategory.ORGANIZATIONAL: 2.0,
            AttributeCategory.UNKNOWN: 1.5,
        }.get(profile.category, 0.0)
        quality = max(0.45, min(1.0, profile.usefulness / 85.0))
        return round(category_base * quality, 2)

    @staticmethod
    def _attribute_view(account: Any) -> dict[str, Any]:
        raw = getattr(account, "raw", None)
        if isinstance(raw, dict):
            return build_attribute_view(raw)
        if isinstance(account, dict):
            return build_attribute_view(account)
        return {}

    def build_keys(self, account: Any) -> set[str]:
        keys: set[str] = set()

        keys.update(build_employee_keys(get_account_value(account, "employee_id")))
        keys.update(build_email_keys(get_account_value(account, "email")))
        keys.update(build_username_keys(get_account_value(account, "username")))
        keys.update(
            build_name_keys(
                display_name=get_account_value(account, "display_name"),
                first_name=get_account_value(account, "first_name"),
                last_name=get_account_value(account, "last_name"),
            )
        )

        if self._dynamic_profiles:
            view = self._attribute_view(account)
            lower_lookup = {str(key).lower(): value for key, value in view.items()}
            for profile in self._dynamic_profiles.values():
                value = view.get(profile.name)
                if value is None:
                    value = lower_lookup.get(profile.name.lower())
                key = self._dynamic_key(profile, value)
                if key:
                    keys.add(key)

        return keys

    def weight(self, key: str) -> float:
        weights = (
            ("employee:exact:", 10.0),
            ("email:exact:", 8.0),
            ("username:exact:", 6.0),
            ("name:exact:", 5.0),
            ("name:first-last:", 4.5),
            ("email:local:", 4.0),
            ("username:prefix6:", 2.0),
            ("name:first-initial-last:", 2.0),
            ("name:prefix6:", 1.5),
            ("username:suffix4:", 1.0),
            ("email:local-prefix6:", 1.0),
        )
        for prefix, value in weights:
            if key.startswith(prefix):
                return value

        if key.startswith("dynamic:"):
            remainder = key[len("dynamic:"):]
            attribute_name = remainder.split(":", 1)[0]
            profile = self._dynamic_profiles.get(attribute_name)
            if profile:
                return self._dynamic_weight(profile)
        return 0.0

    def reason(self, key: str) -> str:
        labels = (
            ("employee:exact:", "Exact employee ID"),
            ("email:exact:", "Exact email"),
            ("email:local:", "Matching email local part"),
            ("username:exact:", "Exact normalized username"),
            ("username:prefix6:", "Matching username prefix"),
            ("username:suffix4:", "Matching username suffix"),
            ("name:exact:", "Exact normalized name"),
            ("name:first-last:", "Matching first and last name"),
            ("name:first-initial-last:", "Matching first initial and last name"),
            ("name:prefix6:", "Matching name prefix"),
        )
        for prefix, label in labels:
            if key.startswith(prefix):
                return label

        if key.startswith("dynamic:"):
            remainder = key[len("dynamic:"):]
            attribute_name = remainder.split(":", 1)[0]
            profile = self._dynamic_profiles.get(attribute_name)
            if profile:
                return f"Exact profiled source attribute: {profile.name}"
        return "Shared blocking key"

    def _allowed(self, account_1: Any, account_2: Any, index_1: int, index_2: int) -> bool:
        if get_source_key(account_1, index_1) == get_source_key(account_2, index_2):
            return False
        if not self.cross_application_only:
            return True
        return normalize_text(get_account_value(account_1, "application")) != normalize_text(
            get_account_value(account_2, "application")
        )

    def _prepare_dynamic_profiles(self, accounts: list[Any]) -> None:
        normalized_accounts = [account for account in accounts if hasattr(account, "raw")]
        profiles = dynamic_blocking_profiles(normalized_accounts)
        self._dynamic_profiles = {
            normalize_text(profile.name).replace(" ", "_"): profile
            for profile in profiles
        }

        if profiles:
            print(
                "[Attribute Profiling] Dynamic blocking attributes="
                + ", ".join(
                    f"{profile.name}({profile.category.value}, usefulness={profile.usefulness})"
                    for profile in profiles
                )
            )
        else:
            print("[Attribute Profiling] No dynamic blocking attributes selected.")

    @staticmethod
    def _value(account: Any, field_name: str) -> str:
        return str(get_account_value(account, field_name) or "").strip()

    def _fuzzy_pair_evidence(
        self,
        account_1: Any,
        account_2: Any,
    ) -> tuple[float, list[str]] | None:
        """Return conservative fuzzy-neighbour evidence for candidate recall.

        A pair must have at least two mutually supporting identity signals.
        No single fuzzy field can create a candidate by itself.
        """
        username_1 = self._value(account_1, "username")
        username_2 = self._value(account_2, "username")
        display_1 = self._value(account_1, "display_name")
        display_2 = self._value(account_2, "display_name")
        first_1 = self._value(account_1, "first_name")
        first_2 = self._value(account_2, "first_name")
        last_1 = self._value(account_1, "last_name")
        last_2 = self._value(account_2, "last_name")
        email_local_1 = self._value(account_1, "email_local_part")
        email_local_2 = self._value(account_2, "email_local_part")

        username_score = username_similarity(username_1, username_2)
        name_score = token_similarity(display_1, display_2)
        first_score = similarity_ratio(first_1, first_2)
        last_score = similarity_ratio(last_1, last_2)
        email_local_score = username_similarity(email_local_1, email_local_2)

        strong_first_last = first_score >= 0.88 and last_score >= 0.90
        name_with_support = (
            name_score >= 0.84
            and (username_score >= 0.66 or email_local_score >= 0.66)
        )
        username_email_support = (
            username_score >= 0.86
            and email_local_score >= 0.76
        )
        first_last_with_support = (
            strong_first_last
            and (username_score >= 0.62 or email_local_score >= 0.62)
        )

        if not (
            name_with_support
            or username_email_support
            or first_last_with_support
        ):
            return None

        evidence: list[tuple[str, float, float]] = []
        if username_score >= 0.66:
            evidence.append(("Similar username", username_score, 2.3))
        if email_local_score >= 0.66:
            evidence.append(("Similar email local part", email_local_score, 2.5))
        if name_score >= 0.80:
            evidence.append(("Similar display name", name_score, 3.0))
        if strong_first_last:
            evidence.append(("Strong first and last name similarity", min(first_score, last_score), 3.0))

        if len(evidence) < 2:
            return None

        weighted_quality = sum(score * weight for _, score, weight in evidence)
        total_weight = sum(weight for _, _, weight in evidence)
        quality = weighted_quality / total_weight if total_weight else 0.0

        # Keep fuzzy candidates above the configured blocking threshold while
        # still ranking stronger fuzzy neighbours ahead of weaker ones.
        blocking_score = max(
            self.minimum_blocking_score,
            round(4.0 + max(0.0, quality - 0.65) * 12.0, 2),
        )
        reasons = [label for label, _, _ in evidence]
        return blocking_score, reasons

    def _should_expand_fuzzy(self, account_count: int, primary_pair_count: int) -> bool:
        if account_count < 2 or account_count > self.FUZZY_EXHAUSTIVE_LIMIT:
            return False

        # If deterministic blocking already produces a healthy candidate
        # neighbourhood, avoid spending CPU on exhaustive fuzzy expansion.
        healthy_pair_floor = max(20, account_count // 2)
        return primary_pair_count < healthy_pair_floor

    def _expand_fuzzy_candidates(
        self,
        accounts: list[Any],
        existing_pairs: set[tuple[int, int]],
    ) -> list[BlockingCandidate]:
        if not self._should_expand_fuzzy(len(accounts), len(existing_pairs)):
            return []

        per_account: dict[int, list[tuple[float, int, list[str]]]] = defaultdict(list)
        evaluated_pairs = 0

        for index_1, index_2 in combinations(range(len(accounts)), 2):
            pair_key = (index_1, index_2)
            if pair_key in existing_pairs:
                continue
            if not self._allowed(accounts[index_1], accounts[index_2], index_1, index_2):
                continue

            evaluated_pairs += 1
            evidence = self._fuzzy_pair_evidence(accounts[index_1], accounts[index_2])
            if evidence is None:
                continue

            score, reasons = evidence
            per_account[index_1].append((score, index_2, reasons))
            per_account[index_2].append((score, index_1, reasons))

        selected_pairs: dict[tuple[int, int], tuple[float, list[str]]] = {}
        neighbour_limit = min(
            self.FUZZY_NEIGHBORS_PER_ACCOUNT,
            max(1, self.max_candidates_per_account // 2),
        )

        for account_index, neighbours in per_account.items():
            neighbours.sort(key=lambda item: (-item[0], item[1]))
            for score, other_index, reasons in neighbours[:neighbour_limit]:
                pair_key = tuple(sorted((account_index, other_index)))
                existing = selected_pairs.get(pair_key)
                if existing is None or score > existing[0]:
                    selected_pairs[pair_key] = (score, reasons)

        fuzzy_candidates = [
            BlockingCandidate(
                account_1_index=index_1,
                account_2_index=index_2,
                account_1=accounts[index_1],
                account_2=accounts[index_2],
                shared_block_keys=["fuzzy:adaptive-neighbour"],
                blocking_score=round(score, 2),
                reasons=["Adaptive fuzzy candidate"] + reasons,
            )
            for (index_1, index_2), (score, reasons) in selected_pairs.items()
        ]

        print(
            "[Candidate Expansion] "
            f"PrimaryPairs={len(existing_pairs)}, "
            f"EvaluatedFuzzyPairs={evaluated_pairs}, "
            f"FuzzyPairsAdded={len(fuzzy_candidates)}, "
            f"NeighborLimit={neighbour_limit}"
        )

        return fuzzy_candidates

    def generate(self, accounts: list[Any]) -> list[BlockingCandidate]:
        if len(accounts) < 2:
            return []

        self._prepare_dynamic_profiles(accounts)
        block_index: dict[str, list[int]] = defaultdict(list)

        for index, account in enumerate(accounts):
            for key in self.build_keys(account):
                block_index[key].append(index)

        pair_keys: dict[tuple[int, int], set[str]] = defaultdict(set)
        for key, indexes in block_index.items():
            if len(indexes) < 2 or len(indexes) > self.max_block_size or self.weight(key) <= 0:
                continue
            for index_1, index_2 in combinations(indexes, 2):
                if self._allowed(accounts[index_1], accounts[index_2], index_1, index_2):
                    pair_keys[(index_1, index_2)].add(key)

        candidates: list[BlockingCandidate] = []
        for (index_1, index_2), keys in pair_keys.items():
            score = sum(self.weight(key) for key in keys)
            if score < self.minimum_blocking_score:
                continue
            sorted_keys = sorted(keys, key=lambda key: (-self.weight(key), key))
            candidates.append(
                BlockingCandidate(
                    account_1_index=index_1,
                    account_2_index=index_2,
                    account_1=accounts[index_1],
                    account_2=accounts[index_2],
                    shared_block_keys=sorted_keys,
                    blocking_score=round(score, 2),
                    reasons=[self.reason(key) for key in sorted_keys],
                )
            )

        primary_pairs = {
            (candidate.account_1_index, candidate.account_2_index)
            for candidate in candidates
        }
        candidates.extend(self._expand_fuzzy_candidates(accounts, primary_pairs))

        candidates.sort(
            key=lambda candidate: (
                -candidate.blocking_score,
                candidate.account_1_index,
                candidate.account_2_index,
            )
        )

        selected: list[BlockingCandidate] = []
        counts: dict[int, int] = defaultdict(int)
        seen_pairs: set[tuple[int, int]] = set()

        for candidate in candidates:
            left = candidate.account_1_index
            right = candidate.account_2_index
            pair_key = tuple(sorted((left, right)))
            if pair_key in seen_pairs:
                continue
            if counts[left] >= self.max_candidates_per_account or counts[right] >= self.max_candidates_per_account:
                continue
            selected.append(candidate)
            seen_pairs.add(pair_key)
            counts[left] += 1
            counts[right] += 1

        return selected


blocking_candidate_generator = BlockingCandidateGenerator()
