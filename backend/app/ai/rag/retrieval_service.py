from __future__ import annotations

from typing import Any

from app.ai.rag.knowledge_index_service import (
    KnowledgeIndexService,
    knowledge_index_service,
)


class KnowledgeRetrievalService:
    """
    Retrieval layer used by the AI knowledge tool.
    """

    def __init__(
        self,
        *,
        index_service: KnowledgeIndexService = (
            knowledge_index_service
        ),
    ) -> None:
        self._index_service = index_service

    @staticmethod
    def normalize_query(
        value: Any,
    ) -> str:
        return " ".join(
            str(
                value or ""
            )
            .strip()
            .split()
        )

    def search(
        self,
        *,
        query: str,
        limit: int = 5,
        minimum_similarity: float = 0.50,
        document_id: int | None = None,
    ) -> dict[str, Any]:

        normalized_query = self.normalize_query(
            query
        )

        if not normalized_query:
            return {
                "found": False,
                "query": "",
                "resultCount": 0,
                "sources": [],
                "message": (
                    "Knowledge search query "
                    "cannot be empty."
                ),
            }

        limit = max(
            1,
            min(
                int(limit),
                8,
            ),
        )

        minimum_similarity = max(
            0.0,
            min(
                float(
                    minimum_similarity
                ),
                1.0,
            ),
        )

        results = self._index_service.search(
            normalized_query,
            limit=limit,
            minimum_similarity=minimum_similarity,
            document_id=document_id,
        )

        sources: list[
            dict[str, Any]
        ] = []

        seen_chunks: set[
            tuple[int, str]
        ] = set()

        for result in results:
            metadata = result.metadata

            key = (
                metadata.document_id,
                metadata.chunk_id,
            )

            if key in seen_chunks:
                continue

            seen_chunks.add(
                key
            )

            sources.append(
                {
                    "documentId":
                        metadata.document_id,

                    "documentName":
                        metadata.document_name,

                    "chunkId":
                        metadata.chunk_id,

                    "chunkIndex":
                        metadata.chunk_index,

                    "pageNumber":
                        metadata.page_number,

                    "contentType":
                        metadata.content_type,

                    "similarity":
                        float(
                            result.score
                        ),

                    "content":
                        metadata.content,

                    "extra":
                        metadata.extra,
                }
            )

        if not sources:
            return {
                "found": False,
                "query": normalized_query,
                "resultCount": 0,
                "minimumSimilarity":
                    minimum_similarity,
                "documentId":
                    document_id,
                "sources": [],
                "message": (
                    "No sufficiently relevant "
                    "knowledge-base content was found."
                ),
            }

        return {
            "found": True,
            "query":
                normalized_query,
            "resultCount":
                len(sources),
            "minimumSimilarity":
                minimum_similarity,
            "documentId":
                document_id,
            "sources":
                sources,
        }


knowledge_retrieval_service = (
    KnowledgeRetrievalService()
)