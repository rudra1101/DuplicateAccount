from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import RLock
from typing import Iterable

import faiss
import numpy as np

from app.ai.vector_store.types import (
    VectorMetadata,
    VectorSearchResult,
)


logger = logging.getLogger(__name__)


DEFAULT_STORE_DIRECTORY = (
    Path(__file__).resolve().parent
    / "data"
)


class FaissVectorStore:
    """
    Persistent cosine-similarity vector store.

    Vectors are normalized before insertion and search.
    FAISS IndexFlatIP therefore returns cosine similarity.

    The FAISS index stores vectors and integer IDs.
    Account metadata is persisted separately as JSON.
    """

    def __init__(
        self,
        *,
        directory: Path = DEFAULT_STORE_DIRECTORY,
        index_filename: str = "accounts.faiss",
        metadata_filename: str = "accounts_metadata.json",
    ) -> None:
        self._directory = directory
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._index_path = (
            self._directory
            / index_filename
        )

        self._metadata_path = (
            self._directory
            / metadata_filename
        )

        self._index: faiss.Index | None = None
        self._dimension: int | None = None

        self._metadata: dict[
            int,
            VectorMetadata,
        ] = {}

        self._lock = RLock()

        self.load()

    @property
    def dimension(self) -> int | None:
        return self._dimension

    @property
    def count(self) -> int:
        if self._index is None:
            return 0

        return int(self._index.ntotal)

    def _create_index(
        self,
        dimension: int,
    ) -> faiss.Index:
        if dimension < 1:
            raise ValueError(
                "Vector dimension must be greater than zero."
            )

        # IndexIDMap2 allows explicit stable vector IDs.
        base_index = faiss.IndexFlatIP(
            dimension
        )

        return faiss.IndexIDMap2(
            base_index
        )

    @staticmethod
    def _as_matrix(
        vectors: Iterable[list[float]],
    ) -> np.ndarray:
        matrix = np.asarray(
            list(vectors),
            dtype=np.float32,
        )

        if matrix.ndim != 2:
            raise ValueError(
                "Vectors must form a two-dimensional matrix."
            )

        if matrix.shape[0] == 0:
            raise ValueError(
                "At least one vector is required."
            )

        if matrix.shape[1] == 0:
            raise ValueError(
                "Embedding vectors cannot be empty."
            )

        if not np.isfinite(matrix).all():
            raise ValueError(
                "Embedding vectors contain invalid numeric values."
            )

        return matrix

    @staticmethod
    def _normalize(
        matrix: np.ndarray,
    ) -> np.ndarray:
        normalized = np.ascontiguousarray(
            matrix,
            dtype=np.float32,
        )

        faiss.normalize_L2(
            normalized
        )

        return normalized

    def _ensure_index(
        self,
        dimension: int,
    ) -> None:
        if self._index is None:
            self._index = self._create_index(
                dimension
            )

            self._dimension = dimension
            return

        if self._dimension != dimension:
            raise ValueError(
                "Embedding dimension does not match "
                "the existing FAISS index. "
                f"Expected {self._dimension}, "
                f"received {dimension}."
            )

    def add(
        self,
        *,
        vectors: list[list[float]],
        metadata: list[VectorMetadata],
        persist: bool = True,
    ) -> None:
        if len(vectors) != len(metadata):
            raise ValueError(
                "The number of vectors must match "
                "the number of metadata records."
            )

        if not vectors:
            return

        matrix = self._normalize(
            self._as_matrix(vectors)
        )

        ids = np.asarray(
            [
                item.vector_id
                for item in metadata
            ],
            dtype=np.int64,
        )

        if len(set(ids.tolist())) != len(ids):
            raise ValueError(
                "Vector IDs must be unique within the batch."
            )

        with self._lock:
            self._ensure_index(
                int(matrix.shape[1])
            )

            existing_ids = {
                int(vector_id)
                for vector_id in ids.tolist()
                if int(vector_id)
                in self._metadata
            }

            if existing_ids:
                raise ValueError(
                    "Vector IDs already exist: "
                    + ", ".join(
                        str(value)
                        for value in sorted(
                            existing_ids
                        )
                    )
                )

            assert self._index is not None

            self._index.add_with_ids(
                matrix,
                ids,
            )

            for item in metadata:
                self._metadata[
                    item.vector_id
                ] = item

            if persist:
                self.save()

        logger.info(
            "Added %s account vector(s). "
            "FAISS index now contains %s vector(s).",
            len(vectors),
            self.count,
        )

    def search(
        self,
        *,
        query_vector: list[float],
        limit: int = 10,
        minimum_similarity: float = 0.0,
        exclude_vector_ids: set[int] | None = None,
        application: str | None = None,
        scan_id: int | None = None,
    ) -> list[VectorSearchResult]:
        if limit < 1:
            raise ValueError(
                "Search limit must be at least 1."
            )

        if self._index is None or self.count == 0:
            return []

        query_matrix = self._normalize(
            self._as_matrix(
                [query_vector]
            )
        )

        if (
            self._dimension
            != query_matrix.shape[1]
        ):
            raise ValueError(
                "Query vector dimension does not "
                "match the FAISS index."
            )

        excluded = (
            exclude_vector_ids
            or set()
        )

        # Request extra results because filtering may
        # remove matches after FAISS returns them.
        search_limit = min(
            self.count,
            max(
                limit * 5,
                limit,
            ),
        )

        with self._lock:
            scores, ids = self._index.search(
                query_matrix,
                search_limit,
            )

        results: list[
            VectorSearchResult
        ] = []

        normalized_application = (
            application.strip().lower()
            if application
            else None
        )

        for score, vector_id in zip(
            scores[0],
            ids[0],
            strict=True,
        ):
            current_id = int(
                vector_id
            )

            if current_id < 0:
                continue

            if current_id in excluded:
                continue

            if float(score) < minimum_similarity:
                continue

            item = self._metadata.get(
                current_id
            )

            if item is None:
                continue

            if (
                scan_id is not None
                and item.scan_id != scan_id
            ):
                continue

            if (
                normalized_application
                and item.application
                .strip()
                .lower()
                != normalized_application
            ):
                continue

            results.append(
                VectorSearchResult(
                    score=round(
                        float(score),
                        6,
                    ),
                    metadata=item,
                )
            )

            if len(results) >= limit:
                break

        return results

    def remove(
        self,
        vector_ids: list[int],
        *,
        persist: bool = True,
    ) -> int:
        if not vector_ids:
            return 0

        if self._index is None:
            return 0

        ids = np.asarray(
            vector_ids,
            dtype=np.int64,
        )

        with self._lock:
            removed = int(
                self._index.remove_ids(
                    ids
                )
            )

            for vector_id in vector_ids:
                self._metadata.pop(
                    vector_id,
                    None,
                )

            if persist:
                self.save()

        return removed

    def metadata_items(
        self,
    ) -> list[
        tuple[int, VectorMetadata]
    ]:
        with self._lock:
            return list(
                self._metadata.items()
            )

    def clear(
        self,
        *,
        persist: bool = True,
    ) -> None:
        with self._lock:
            self._index = None
            self._dimension = None
            self._metadata.clear()

            if persist:
                if self._index_path.exists():
                    self._index_path.unlink()

                if self._metadata_path.exists():
                    self._metadata_path.unlink()

    def save(self) -> None:
        with self._lock:
            if self._index is not None:
                faiss.write_index(
                    self._index,
                    str(self._index_path),
                )

            metadata_payload = {
                str(vector_id): item.to_dict()
                for vector_id, item
                in self._metadata.items()
            }

            temporary_path = (
                self._metadata_path
                .with_suffix(".tmp")
            )

            temporary_path.write_text(
                json.dumps(
                    metadata_payload,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                self._metadata_path
            )

    def load(self) -> None:
        with self._lock:
            if self._index_path.exists():
                self._index = (
                    faiss.read_index(
                        str(
                            self._index_path
                        )
                    )
                )

                self._dimension = int(
                    self._index.d
                )

            if self._metadata_path.exists():
                raw_metadata = json.loads(
                    self._metadata_path
                    .read_text(
                        encoding="utf-8"
                    )
                )

                self._metadata = {
                    int(vector_id): (
                        VectorMetadata.from_dict(
                            value
                        )
                    )
                    for vector_id, value
                    in raw_metadata.items()
                }

            if (
                self._index is not None
                and self.count
                != len(self._metadata)
            ):
                logger.warning(
                    "FAISS vector count (%s) does not "
                    "match metadata count (%s).",
                    self.count,
                    len(self._metadata),
                )


faiss_account_store = (
    FaissVectorStore()
)