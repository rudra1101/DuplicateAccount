from __future__ import annotations

import json
import logging

from pathlib import Path
from threading import RLock
from typing import Iterable

import faiss
import numpy as np

from app.ai.rag.types import (
    KnowledgeSearchResult,
    KnowledgeVectorMetadata,
)


logger = logging.getLogger(
    __name__
)


DEFAULT_KNOWLEDGE_DIRECTORY = (
    Path(
        __file__
    )
    .resolve()
    .parent
    / "data"
)


class KnowledgeFaissStore:
    def __init__(
        self,
        *,
        directory: Path = DEFAULT_KNOWLEDGE_DIRECTORY,
        index_filename: str = "knowledge.faiss",
        metadata_filename: str = "knowledge_metadata.json",
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
            KnowledgeVectorMetadata,
        ] = {}
    
        self._lock = RLock()
    
        self.load()
    
    @property
    def count(
        self,
    ) -> int:
        if self._index is None:
            return 0

        return int(
            self._index.ntotal
        )

    @property
    def dimension(
        self,
    ) -> int | None:
        return self._dimension

    def _create_index(
        self,
        dimension: int,
    ) -> faiss.Index:

        if dimension < 1:
            raise ValueError(
                "Vector dimension must be greater than zero."
            )

        base_index = (
            faiss.IndexFlatIP(
                dimension
            )
        )

        return (
            faiss.IndexIDMap2(
                base_index
            )
        )

    @staticmethod
    def _as_matrix(
        vectors: Iterable[
            list[float]
        ],
    ) -> np.ndarray:

        matrix = np.asarray(
            list(
                vectors
            ),
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

        if not np.isfinite(
            matrix
        ).all():
            raise ValueError(
                "Embedding vectors contain invalid numeric values."
            )

        return matrix

    @staticmethod
    def _normalize(
        matrix: np.ndarray,
    ) -> np.ndarray:

        normalized = (
            np.ascontiguousarray(
                matrix,
                dtype=np.float32,
            )
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
            self._index = (
                self._create_index(
                    dimension
                )
            )

            self._dimension = (
                dimension
            )

            return

        if (
            self._dimension
            != dimension
        ):
            raise ValueError(
                "Embedding dimension does not match "
                "the existing knowledge FAISS index."
            )

    def add(
        self,
        *,
        vectors: list[
            list[float]
        ],
        metadata: list[
            KnowledgeVectorMetadata
        ],
        persist: bool = True,
    ) -> None:

        if (
            len(vectors)
            != len(metadata)
        ):
            raise ValueError(
                "The number of vectors must match "
                "the number of metadata records."
            )

        if not vectors:
            return

        matrix = self._normalize(
            self._as_matrix(
                vectors
            )
        )

        ids = np.asarray(
            [
                item.vector_id
                for item
                in metadata
            ],
            dtype=np.int64,
        )

        if (
            len(
                set(
                    ids.tolist()
                )
            )
            != len(ids)
        ):
            raise ValueError(
                "Knowledge vector IDs must be unique."
            )

        with self._lock:
            self._ensure_index(
                int(
                    matrix.shape[1]
                )
            )

            existing_ids = {
                int(
                    vector_id
                )
                for vector_id
                in ids.tolist()
                if int(
                    vector_id
                )
                in self._metadata
            }

            if existing_ids:
                raise ValueError(
                    "Knowledge vector IDs already exist: "
                    + ", ".join(
                        str(
                            value
                        )
                        for value
                        in sorted(
                            existing_ids
                        )
                    )
                )

            assert (
                self._index
                is not None
            )

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
            "Added %s knowledge vector(s). "
            "Knowledge index now contains %s vector(s).",
            len(vectors),
            self.count,
        )

    def search(
        self,
        *,
        query_vector: list[float],
        limit: int = 5,
        minimum_similarity: float = 0.50,
        document_id: int | None = None,
    ) -> list[
        KnowledgeSearchResult
    ]:

        if limit < 1:
            raise ValueError(
                "Search limit must be at least 1."
            )

        if (
            self._index is None
            or self.count == 0
        ):
            return []

        query_matrix = (
            self._normalize(
                self._as_matrix(
                    [
                        query_vector
                    ]
                )
            )
        )

        if (
            self._dimension
            != query_matrix.shape[1]
        ):
            raise ValueError(
                "Query vector dimension does not "
                "match the knowledge index."
            )

        search_limit = min(
            self.count,
            max(
                limit * 5,
                limit,
            ),
        )

        with self._lock:
            scores, ids = (
                self._index.search(
                    query_matrix,
                    search_limit,
                )
            )

        results: list[
            KnowledgeSearchResult
        ] = []

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

            if (
                float(score)
                < minimum_similarity
            ):
                continue

            metadata = (
                self._metadata.get(
                    current_id
                )
            )

            if metadata is None:
                continue

            if (
                document_id
                is not None
                and metadata.document_id
                != document_id
            ):
                continue

            results.append(
                KnowledgeSearchResult(
                    score=round(
                        float(
                            score
                        ),
                        6,
                    ),
                    metadata=metadata,
                )
            )

            if (
                len(results)
                >= limit
            ):
                break

        return results

    def remove_document(
        self,
        document_id: int,
        *,
        persist: bool = True,
    ) -> int:

        vector_ids = [
            vector_id
            for vector_id, metadata
            in self._metadata.items()
            if metadata.document_id
            == document_id
        ]

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

            for vector_id in (
                vector_ids
            ):
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
        tuple[
            int,
            KnowledgeVectorMetadata,
        ]
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

            self._dimension = (
                None
            )

            self._metadata.clear()

            if persist:
                if (
                    self._index_path.exists()
                ):
                    self._index_path.unlink()

                if (
                    self._metadata_path.exists()
                ):
                    self._metadata_path.unlink()

    def save(
        self,
    ) -> None:

        with self._lock:
            if self._index is not None:
                faiss.write_index(
                    self._index,
                    str(
                        self._index_path
                    ),
                )

            metadata_payload = {
                str(
                    vector_id
                ):
                    metadata.to_dict()

                for vector_id, metadata
                in self._metadata.items()
            }

            temporary_path = (
                self._metadata_path
                .with_suffix(
                    ".tmp"
                )
            )

            temporary_path.write_text(
                json.dumps(
                    metadata_payload,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                self._metadata_path
            )

    def load(
        self,
    ) -> None:

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

            if (
                self._metadata_path.exists()
            ):
                raw_metadata = (
                    json.loads(
                        self._metadata_path
                        .read_text(
                            encoding="utf-8"
                        )
                    )
                )

                self._metadata = {
                    int(vector_id):
                        KnowledgeVectorMetadata
                        .from_dict(
                            value
                        )

                    for vector_id, value
                    in raw_metadata.items()
                }

            if (
                self._index is not None
                and self.count
                != len(
                    self._metadata
                )
            ):
                logger.warning(
                    "Knowledge FAISS vector count (%s) "
                    "does not match metadata count (%s).",
                    self.count,
                    len(
                        self._metadata
                    ),
                )


knowledge_vector_store = (
    KnowledgeFaissStore()
)