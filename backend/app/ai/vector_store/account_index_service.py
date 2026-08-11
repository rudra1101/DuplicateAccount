from __future__ import annotations

import logging
from typing import Any

from app.ai.duplicate_engine.embedding_features import (
    build_identity_embedding_text,
)
from app.ai.duplicate_engine.normalizer import (
    normalize_account,
)
from app.ai.embeddings import (
    embedding_service,
)
from app.ai.vector_store.faiss_store import (
    FaissVectorStore,
    faiss_account_store,
)
from app.ai.vector_store.types import (
    VectorMetadata,
    VectorSearchResult,
)


logger = logging.getLogger(__name__)


class AccountVectorIndexService:
    def __init__(
        self,
        store: FaissVectorStore = (
            faiss_account_store
        ),
    ) -> None:
        self._store = store

    @staticmethod
    def build_vector_id(
        *,
        scan_id: int,
        account_record_id: int,
    ) -> int:
        if scan_id < 1:
            raise ValueError(
                "scan_id must be greater than zero."
            )

        if account_record_id < 1:
            raise ValueError(
                "account_record_id must be greater than zero."
            )

        return (
            scan_id * 10_000_000
            + account_record_id
        )

    def index_accounts(
        self,
        *,
        scan_id: int,
        accounts: list[dict[str, Any]],
        account_record_ids: list[int],
    ) -> int:
        if len(accounts) != len(
            account_record_ids
        ):
            raise ValueError(
                "Accounts and account record IDs "
                "must have the same length."
            )

        if not accounts:
            return 0

        normalized_accounts = [
            normalize_account(account)
            for account in accounts
        ]

        embedding_texts = [
            build_identity_embedding_text(
                account
            )
            for account in normalized_accounts
        ]

        logger.info(
            "Generating %s identity vector(s) "
            "for scan %s.",
            len(embedding_texts),
            scan_id,
        )

        vectors = embedding_service.embed_many(
            embedding_texts
        )

        metadata: list[
            VectorMetadata
        ] = []

        usable_vectors: list[
            list[float]
        ] = []

        for (
            raw_account,
            normalized_account,
            account_record_id,
            vector,
        ) in zip(
            accounts,
            normalized_accounts,
            account_record_ids,
            vectors,
            strict=True,
        ):
            if not vector:
                continue

            vector_id = self.build_vector_id(
                scan_id=scan_id,
                account_record_id=(
                    account_record_id
                ),
            )

            metadata.append(
                VectorMetadata(
                    vector_id=vector_id,
                    scan_id=scan_id,
                    source_account_id=(
                        normalized_account
                        .original_id()
                    ),
                    application=str(
                        raw_account.get(
                            "application",
                            "",
                        )
                        or ""
                    ),
                    username=str(
                        raw_account.get(
                            "username",
                            "",
                        )
                        or ""
                    ),
                    display_name=str(
                        raw_account.get(
                            "displayName",
                            "",
                        )
                        or ""
                    ),
                    email=str(
                        raw_account.get(
                            "email",
                            "",
                        )
                        or ""
                    ),
                    employee_id=str(
                        raw_account.get(
                            "employeeId",
                            "",
                        )
                        or ""
                    ),
                    embedding_model=(
                        embedding_service.model
                    ),
                    extra={
                        "department": (
                            raw_account.get(
                                "department"
                            )
                        ),
                        "manager": (
                            raw_account.get(
                                "manager"
                            )
                        ),
                        "status": (
                            raw_account.get(
                                "status"
                            )
                        ),
                    },
                )
            )

            usable_vectors.append(
                vector
            )

        self._store.add(
            vectors=usable_vectors,
            metadata=metadata,
            persist=True,
        )

        return len(
            usable_vectors
        )

    def find_vector_ids(
        self,
        *,
        source_account_id: str | None = None,
        application: str | None = None,
        scan_id: int | None = None,
    ) -> set[int]:
        excluded: set[int] = set()

        normalized_source_id = (
            str(
                source_account_id
                or ""
            )
            .strip()
            .lower()
        )

        normalized_application = (
            str(
                application
                or ""
            )
            .strip()
            .lower()
        )

        for (
            vector_id,
            metadata,
        ) in self._store.metadata_items():
            if (
                scan_id is not None
                and metadata.scan_id
                != scan_id
            ):
                continue

            if (
                normalized_source_id
                and metadata
                .source_account_id
                .strip()
                .lower()
                != normalized_source_id
            ):
                continue

            if (
                normalized_application
                and metadata
                .application
                .strip()
                .lower()
                != normalized_application
            ):
                continue

            excluded.add(
                vector_id
            )

        return excluded

    def search_account(
        self,
        account: dict[str, Any],
        *,
        limit: int = 10,
        minimum_similarity: float = 0.70,
        scan_id: int | None = None,
        application: str | None = None,
        source_account_id: str | None = None,
        exclude_vector_id: int | None = None,
    ) -> list[VectorSearchResult]:
        normalized = normalize_account(
            account
        )

        text = build_identity_embedding_text(
            normalized
        )

        vector = embedding_service.embed(
            text
        )

        if not vector:
            return []

        excluded_vector_ids: set[int] = set()

        if exclude_vector_id is not None:
            excluded_vector_ids.add(
                exclude_vector_id
            )

        if source_account_id:
            excluded_vector_ids.update(
                self.find_vector_ids(
                    source_account_id=(
                        source_account_id
                    ),
                    application=account.get(
                        "application"
                    ),
                    scan_id=scan_id,
                )
            )

        return self._store.search(
            query_vector=vector,
            limit=limit,
            minimum_similarity=(
                minimum_similarity
            ),
            scan_id=scan_id,
            application=application,
            exclude_vector_ids=(
                excluded_vector_ids
            ),
        )

    def search_text(
        self,
        query: str,
        *,
        limit: int = 10,
        minimum_similarity: float = 0.60,
        scan_id: int | None = None,
    ) -> list[VectorSearchResult]:
        vector = embedding_service.embed(
            query
        )

        if not vector:
            return []

        return self._store.search(
            query_vector=vector,
            limit=limit,
            minimum_similarity=(
                minimum_similarity
            ),
            scan_id=scan_id,
        )


account_vector_index_service = (
    AccountVectorIndexService()
)