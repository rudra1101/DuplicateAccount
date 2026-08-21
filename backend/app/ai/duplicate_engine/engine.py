from __future__ import annotations

import logging
from typing import Any

from app.ai.blocking import BlockingCandidateGenerator
from app.ai.duplicate_engine.attribute_profiler import (
    AttributeProfile,
    dynamic_blocking_profiles,
)
from app.ai.duplicate_engine.embedding_features import (
    AccountEmbeddingProfile,
    get_embedding_profile_key,
    precompute_embedding_profiles,
)
from app.ai.duplicate_engine.explanation_engine import build_explanation
from app.ai.duplicate_engine.feature_extractor import extract_features
from app.ai.duplicate_engine.hybrid_score import calculate_hybrid_score, classify_confidence
from app.ai.duplicate_engine.normalizer import normalize_account
from app.ai.duplicate_engine.types import DuplicatePrediction, NormalizedAccount


logger = logging.getLogger(__name__)


class DuplicateDetectionEngine:
    def normalize_accounts(self, accounts: list[dict[str, Any]]) -> list[NormalizedAccount]:
        logger.info("Normalizing %s account(s).", len(accounts))
        normalized_accounts = [normalize_account(account) for account in accounts]
        logger.info("Account normalization completed.")
        return normalized_accounts

    def prepare_embedding_profiles(
        self,
        accounts: list[NormalizedAccount],
    ) -> dict[str, AccountEmbeddingProfile]:
        if not accounts:
            return {}
        logger.info("Preparing embedding profiles for %s account(s).", len(accounts))
        profiles = precompute_embedding_profiles(accounts)
        logger.info("Prepared %s embedding profile(s).", len(profiles))
        return profiles

    @staticmethod
    def build_source_key(account: NormalizedAccount) -> str:
        application = str(account.application or "").strip().lower()
        source_id = str(account.original_id() or "").strip().lower()
        if source_id:
            return f"{application}:{source_id}"
        username = str(account.username or "").strip().lower()
        return f"{application}:username:{username}"

    def compare_normalized(
        self,
        account_1: NormalizedAccount,
        account_2: NormalizedAccount,
        *,
        include_embeddings: bool = True,
        embedding_profiles: dict[str, AccountEmbeddingProfile] | None = None,
        attribute_profiles: list[AttributeProfile] | None = None,
    ) -> DuplicatePrediction:
        account_1_key = self.build_source_key(account_1)
        account_2_key = self.build_source_key(account_2)
        if account_1_key == account_2_key:
            raise ValueError("Cannot compare an account with itself.")

        profile_1: AccountEmbeddingProfile | None = None
        profile_2: AccountEmbeddingProfile | None = None
        if include_embeddings and embedding_profiles is not None:
            profile_1 = embedding_profiles.get(get_embedding_profile_key(account_1))
            profile_2 = embedding_profiles.get(get_embedding_profile_key(account_2))

        features = extract_features(
            account_1,
            account_2,
            include_embeddings=include_embeddings,
            embedding_profile_1=profile_1,
            embedding_profile_2=profile_2,
            attribute_profiles=attribute_profiles,
        )
        confidence = calculate_hybrid_score(features)
        reasons, warnings = build_explanation(features)

        if features.dynamic_matched_attributes:
            reasons.append(
                type(reasons[0])(
                    field="dynamicSourceAttributes",
                    message=(
                        "Matching profiled source attributes: "
                        + ", ".join(features.dynamic_matched_attributes[:5])
                    ),
                    impact="positive",
                    similarity=1.0,
                )
                if reasons
                else __import__("app.ai.duplicate_engine.types", fromlist=["MatchReason"]).MatchReason(
                    field="dynamicSourceAttributes",
                    message=(
                        "Matching profiled source attributes: "
                        + ", ".join(features.dynamic_matched_attributes[:5])
                    ),
                    impact="positive",
                    similarity=1.0,
                )
            )
        if features.dynamic_conflicting_attributes:
            warnings.append(
                __import__("app.ai.duplicate_engine.types", fromlist=["MatchReason"]).MatchReason(
                    field="dynamicSourceAttributes",
                    message=(
                        "Conflicting strong source attributes: "
                        + ", ".join(features.dynamic_conflicting_attributes[:5])
                    ),
                    impact="negative",
                    similarity=0.0,
                )
            )

        model_version = (
            "hybrid-profiled-embedding-v4"
            if include_embeddings
            else "hybrid-profiled-rules-v3"
        )
        return DuplicatePrediction(
            account_1=account_1,
            account_2=account_2,
            confidence=confidence,
            classification=classify_confidence(confidence),
            features=features,
            reasons=reasons,
            warnings=warnings,
            model_version=model_version,
        )

    def compare(
        self,
        account_1: dict[str, Any] | NormalizedAccount,
        account_2: dict[str, Any] | NormalizedAccount,
        *,
        include_embeddings: bool = True,
        embedding_profiles: dict[str, AccountEmbeddingProfile] | None = None,
    ) -> DuplicatePrediction:
        normalized_1 = account_1 if isinstance(account_1, NormalizedAccount) else normalize_account(account_1)
        normalized_2 = account_2 if isinstance(account_2, NormalizedAccount) else normalize_account(account_2)
        return self.compare_normalized(
            normalized_1,
            normalized_2,
            include_embeddings=include_embeddings,
            embedding_profiles=embedding_profiles,
        )

    def detect(
        self,
        accounts: list[dict[str, Any]],
        *,
        minimum_confidence: float = 80,
        cross_application_only: bool = False,
        include_embeddings: bool = True,
        max_block_size: int = 100,
        max_candidates_per_account: int = 25,
        minimum_blocking_score: float = 2.0,
    ) -> list[DuplicatePrediction]:
        if len(accounts) < 2:
            return []

        logger.info("Starting duplicate detection for %s account(s).", len(accounts))
        normalized_accounts = self.normalize_accounts(accounts)
        attribute_profiles = dynamic_blocking_profiles(normalized_accounts)

        if attribute_profiles:
            logger.info(
                "Selected %s profiled source attribute(s) for dynamic evidence.",
                len(attribute_profiles),
            )

        candidate_generator = BlockingCandidateGenerator(
            max_block_size=max_block_size,
            max_candidates_per_account=max_candidates_per_account,
            minimum_blocking_score=minimum_blocking_score,
            cross_application_only=cross_application_only,
        )
        blocking_candidates = candidate_generator.generate(normalized_accounts)

        print(
            "[Blocking] "
            f"Accounts={len(normalized_accounts)}, "
            f"CandidatePairs={len(blocking_candidates)}, "
            f"MaxBlockSize={max_block_size}, "
            f"MaxCandidatesPerAccount={max_candidates_per_account}, "
            f"MinimumBlockingScore={minimum_blocking_score}"
        )

        if not blocking_candidates:
            return []

        embedding_profiles: dict[str, AccountEmbeddingProfile] | None = None
        embeddings_enabled = include_embeddings
        if embeddings_enabled:
            candidate_indexes: set[int] = set()
            for candidate in blocking_candidates:
                candidate_indexes.add(candidate.account_1_index)
                candidate_indexes.add(candidate.account_2_index)
            candidate_accounts = [normalized_accounts[index] for index in sorted(candidate_indexes)]
            try:
                embedding_profiles = self.prepare_embedding_profiles(candidate_accounts)
            except Exception:
                logger.exception(
                    "Embedding precomputation failed. Continuing with rule-based features."
                )
                embeddings_enabled = False
                embedding_profiles = None

        predictions: list[DuplicatePrediction] = []
        compared_pairs: set[tuple[str, str]] = set()
        candidate_count = len(blocking_candidates)

        for index, candidate in enumerate(blocking_candidates, start=1):
            account_1 = candidate.account_1
            account_2 = candidate.account_2
            account_1_key = self.build_source_key(account_1)
            account_2_key = self.build_source_key(account_2)
            if account_1_key == account_2_key:
                continue
            pair_key = tuple(sorted((account_1_key, account_2_key)))
            if pair_key in compared_pairs:
                continue
            compared_pairs.add(pair_key)

            prediction = self.compare_normalized(
                account_1,
                account_2,
                include_embeddings=embeddings_enabled,
                embedding_profiles=embedding_profiles,
                attribute_profiles=attribute_profiles,
            )
            if prediction.confidence >= minimum_confidence:
                predictions.append(prediction)

            if index % 100 == 0 or index == candidate_count:
                logger.info("Compared %s/%s blocked candidate pair(s).", index, candidate_count)

        predictions.sort(
            key=lambda item: (
                -item.confidence,
                self.build_source_key(item.account_1),
                self.build_source_key(item.account_2),
            )
        )
        print(
            "[Duplicate Detection] "
            f"BlockedCandidates={candidate_count}, "
            f"ComparedPairs={len(compared_pairs)}, "
            f"Predictions={len(predictions)}, "
            f"MinimumConfidence={minimum_confidence}"
        )
        return predictions


duplicate_detection_engine = DuplicateDetectionEngine()
