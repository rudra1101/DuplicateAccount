from __future__ import annotations

import hashlib
import logging

from app.ai.embeddings import (
    embedding_service,
)
from app.ai.rag.knowledge_store import (
    KnowledgeFaissStore,
    knowledge_vector_store,
)
from app.ai.rag.types import (
    KnowledgeChunk,
    KnowledgeSearchResult,
    KnowledgeVectorMetadata,
)


logger = logging.getLogger(
    __name__
)


class KnowledgeIndexService:
    def __init__(
        self,
        *,
        store: KnowledgeFaissStore = (
            knowledge_vector_store
        ),
    ) -> None:

        self._store = (
            store
        )

    @staticmethod
    def build_vector_id(
        *,
        document_id: int,
        chunk_index: int,
        chunk_id: str,
    ) -> int:

        payload = (
            f"{document_id}:"
            f"{chunk_index}:"
            f"{chunk_id}"
        ).encode(
            "utf-8"
        )

        digest = (
            hashlib.sha256(
                payload
            ).digest()
        )

        # Keep within signed int64 range.
        return int.from_bytes(
            digest[:8],
            byteorder="big",
            signed=False,
        ) & 0x7FFFFFFFFFFFFFFF

    def index_chunks(
        self,
        *,
        chunks: list[
            KnowledgeChunk
        ],
    ) -> int:

        if not chunks:
            return 0

        texts = [
            chunk.content
            for chunk
            in chunks
            if chunk.content.strip()
        ]

        usable_chunks = [
            chunk
            for chunk
            in chunks
            if chunk.content.strip()
        ]

        if not texts:
            return 0

        logger.info(
            "Generating %s knowledge embedding(s).",
            len(
                texts
            ),
        )

        vectors = (
            embedding_service
            .embed_many(
                texts
            )
        )

        metadata: list[
            KnowledgeVectorMetadata
        ] = []

        usable_vectors: list[
            list[float]
        ] = []

        for chunk, vector in zip(
            usable_chunks,
            vectors,
            strict=True,
        ):
            if not vector:
                continue

            vector_id = (
                self.build_vector_id(
                    document_id=(
                        chunk.document_id
                    ),
                    chunk_index=(
                        chunk.chunk_index
                    ),
                    chunk_id=(
                        chunk.chunk_id
                    ),
                )
            )

            metadata.append(
                KnowledgeVectorMetadata(
                    vector_id=(
                        vector_id
                    ),

                    document_id=(
                        chunk.document_id
                    ),

                    document_name=(
                        chunk.document_name
                    ),

                    chunk_id=(
                        chunk.chunk_id
                    ),

                    chunk_index=(
                        chunk.chunk_index
                    ),

                    content=(
                        chunk.content
                    ),

                    page_number=(
                        chunk.page_number
                    ),

                    content_type=(
                        chunk.content_type
                    ),

                    embedding_model=(
                        embedding_service
                        .model
                    ),

                    extra=(
                        chunk.extra
                        or {}
                    ),
                )
            )

            usable_vectors.append(
                vector
            )

        if not usable_vectors:
            return 0

        self._store.add(
            vectors=(
                usable_vectors
            ),
            metadata=(
                metadata
            ),
            persist=True,
        )

        return len(
            usable_vectors
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        minimum_similarity: float = 0.50,
        document_id: int | None = None,
    ) -> list[
        KnowledgeSearchResult
    ]:

        query = (
            str(
                query
                or ""
            )
            .strip()
        )

        if not query:
            return []

        vector = (
            embedding_service
            .embed(
                query
            )
        )

        if not vector:
            return []

        return (
            self._store.search(
                query_vector=(
                    vector
                ),

                limit=(
                    limit
                ),

                minimum_similarity=(
                    minimum_similarity
                ),

                document_id=(
                    document_id
                ),
            )
        )

    def remove_document(
        self,
        document_id: int,
    ) -> int:

        return (
            self._store
            .remove_document(
                document_id,
                persist=True,
            )
        )

    def clear(
        self,
    ) -> None:
        self._store.clear(
            persist=True
        )

    def count(
        self,
    ) -> int:
        return (
            self._store.count
        )


knowledge_index_service = (
    KnowledgeIndexService()
)