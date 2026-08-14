from __future__ import annotations

import re
from typing import Any

from app.ai.rag.types import (
    KnowledgeChunk,
)


class TextChunker:
    def __init__(
        self,
        *,
        chunk_size: int = 1200,
        overlap: int = 200,
    ) -> None:

        if chunk_size < 100:
            raise ValueError(
                "chunk_size must be at least 100."
            )

        if overlap < 0:
            raise ValueError(
                "overlap cannot be negative."
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

        self._chunk_size = (
            chunk_size
        )

        self._overlap = (
            overlap
        )

    @staticmethod
    def normalize_text(
        text: str,
    ) -> str:
        if not text:
            return ""

        normalized = (
            text.replace(
                "\r\n",
                "\n",
            )
            .replace(
                "\r",
                "\n",
            )
        )

        normalized = re.sub(
            r"[ \t]+",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"\n{3,}",
            "\n\n",
            normalized,
        )

        return (
            normalized
            .strip()
        )

    def _split_text(
        self,
        text: str,
    ) -> list[str]:

        text = (
            self.normalize_text(
                text
            )
        )

        if not text:
            return []

        if (
            len(text)
            <= self._chunk_size
        ):
            return [
                text
            ]

        chunks: list[str] = []

        start = 0

        while start < len(text):
            end = min(
                start
                + self._chunk_size,
                len(text),
            )

            chunk = text[
                start:end
            ]

            # Try to break at a natural boundary.
            if end < len(text):
                boundary = max(
                    chunk.rfind(
                        "\n\n"
                    ),
                    chunk.rfind(
                        ". "
                    ),
                    chunk.rfind(
                        "\n"
                    ),
                    chunk.rfind(
                        " "
                    ),
                )

                # Avoid creating tiny chunks.
                if (
                    boundary
                    >= int(
                        self._chunk_size
                        * 0.60
                    )
                ):
                    end = (
                        start
                        + boundary
                        + 1
                    )

                    chunk = text[
                        start:end
                    ]

            chunk = (
                chunk.strip()
            )

            if chunk:
                chunks.append(
                    chunk
                )

            if end >= len(text):
                break

            start = max(
                end
                - self._overlap,
                start + 1,
            )

        return chunks

    def chunk_document(
        self,
        *,
        document_id: int,
        document_name: str,
        text: str,
        page_number: int | None = None,
        content_type: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> list[KnowledgeChunk]:

        raw_chunks = (
            self._split_text(
                text
            )
        )

        chunks: list[
            KnowledgeChunk
        ] = []

        for index, content in enumerate(
            raw_chunks
        ):
            chunks.append(
                KnowledgeChunk(
                    document_id=(
                        document_id
                    ),

                    document_name=(
                        document_name
                    ),

                    chunk_id=(
                        f"{document_id}:"
                        f"{page_number or 0}:"
                        f"{index}"
                    ),

                    chunk_index=index,

                    content=content,

                    page_number=(
                        page_number
                    ),

                    content_type=(
                        content_type
                    ),

                    extra=(
                        extra
                        or {}
                    ),
                )
            )

        return chunks


text_chunker = (
    TextChunker(
        chunk_size=1200,
        overlap=200,
    )
)