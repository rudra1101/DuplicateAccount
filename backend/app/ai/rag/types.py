from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from typing import Any


@dataclass(frozen=True)
class KnowledgeVectorMetadata:
    vector_id: int
    document_id: int

    document_name: str

    chunk_id: str
    chunk_index: int

    content: str

    page_number: int | None
    content_type: str | None

    embedding_model: str

    extra: dict[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
    ) -> "KnowledgeVectorMetadata":
        return cls(
            vector_id=int(
                value[
                    "vector_id"
                ]
            ),

            document_id=int(
                value[
                    "document_id"
                ]
            ),

            document_name=str(
                value.get(
                    "document_name",
                    "",
                )
            ),

            chunk_id=str(
                value.get(
                    "chunk_id",
                    "",
                )
            ),

            chunk_index=int(
                value.get(
                    "chunk_index",
                    0,
                )
            ),

            content=str(
                value.get(
                    "content",
                    "",
                )
            ),

            page_number=(
                int(
                    value[
                        "page_number"
                    ]
                )
                if value.get(
                    "page_number"
                )
                is not None
                else None
            ),

            content_type=(
                str(
                    value[
                        "content_type"
                    ]
                )
                if value.get(
                    "content_type"
                )
                is not None
                else None
            ),

            embedding_model=str(
                value.get(
                    "embedding_model",
                    "",
                )
            ),

            extra=dict(
                value.get(
                    "extra",
                    {},
                )
            ),
        )


@dataclass(frozen=True)
class KnowledgeSearchResult:
    score: float
    metadata: KnowledgeVectorMetadata

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "similarity":
                self.score,

            "document": {
                "documentId":
                    self.metadata.document_id,

                "documentName":
                    self.metadata.document_name,

                "chunkId":
                    self.metadata.chunk_id,

                "chunkIndex":
                    self.metadata.chunk_index,

                "pageNumber":
                    self.metadata.page_number,

                "contentType":
                    self.metadata.content_type,

                "content":
                    self.metadata.content,

                "embeddingModel":
                    self.metadata.embedding_model,

                "extra":
                    self.metadata.extra,
            },
        }


@dataclass(frozen=True)
class KnowledgeChunk:
    document_id: int
    document_name: str

    chunk_id: str
    chunk_index: int

    content: str

    page_number: int | None = None
    content_type: str | None = None

    extra: dict[str, Any] | None = None