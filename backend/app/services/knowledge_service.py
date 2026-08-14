from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.rag.chunker import (
    text_chunker,
)
from app.ai.rag.document_parser import (
    document_parser,
)
from app.ai.rag.knowledge_index_service import (
    knowledge_index_service,
)
from app.db_models.knowledge_chunk import (
    KnowledgeChunkRecord,
)
from app.db_models.knowledge_document import (
    KnowledgeDocumentRecord,
)


def document_to_dict(
    document: KnowledgeDocumentRecord,
) -> dict[str, Any]:
    return {
        "id":
            document.id,

        "name":
            document.name,

        "originalFilename":
            document.original_filename,

        "contentType":
            document.content_type,

        "status":
            document.status,

        "chunkCount":
            document.chunk_count,

        "characterCount":
            document.character_count,

        "errorMessage":
            document.error_message,

        "createdAt": (
            document.created_at.isoformat()
            if document.created_at
            else None
        ),

        "updatedAt": (
            document.updated_at.isoformat()
            if document.updated_at
            else None
        ),
    }


def chunk_to_dict(
    chunk: KnowledgeChunkRecord,
) -> dict[str, Any]:
    return {
        "id":
            chunk.id,

        "chunkId":
            chunk.chunk_id,

        "chunkIndex":
            chunk.chunk_index,

        "pageNumber":
            chunk.page_number,

        "content":
            chunk.content,

        "characterCount":
            chunk.character_count,

        "createdAt": (
            chunk.created_at.isoformat()
            if chunk.created_at
            else None
        ),
    }


def upload_knowledge_document(
    *,
    db: Session,
    filename: str,
    content: bytes,
    content_type: str | None,
    display_name: str | None = None,
) -> dict[str, Any]:

    parsed = document_parser.parse(
        filename=filename,
        content=content,
        content_type=content_type,
    )

    name = str(
        display_name
        or filename
    ).strip()

    document = KnowledgeDocumentRecord(
        name=name,
        original_filename=(
            parsed.filename
        ),
        content_type=(
            parsed.content_type
        ),
        status="PROCESSING",
        character_count=len(
            parsed.full_text
        ),
        chunk_count=0,
        error_message=None,
    )

    db.add(
        document
    )

    db.flush()

    document_id = (
        document.id
    )

    all_chunks = []

    try:
        global_chunk_index = 0

        for page in parsed.pages:

            page_chunks = (
                text_chunker
                .chunk_document(
                    document_id=(
                        document_id
                    ),
                    document_name=(
                        document.name
                    ),
                    text=(
                        page.text
                    ),
                    page_number=(
                        page.page_number
                    ),
                    content_type=(
                        parsed.content_type
                    ),
                    extra={
                        "originalFilename":
                            parsed.filename,
                    },
                )
            )

            for chunk in page_chunks:

                corrected_chunk = (
                    chunk.__class__(
                        document_id=(
                            document_id
                        ),
                        document_name=(
                            chunk.document_name
                        ),
                        chunk_id=(
                            f"{document_id}:"
                            f"{global_chunk_index}"
                        ),
                        chunk_index=(
                            global_chunk_index
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
                        extra=(
                            chunk.extra
                        ),
                    )
                )

                all_chunks.append(
                    corrected_chunk
                )

                global_chunk_index += 1

        if not all_chunks:
            raise ValueError(
                "The document produced no usable chunks."
            )

        # -----------------------------------------
        # Save chunks to database
        # -----------------------------------------

        for chunk in all_chunks:
            db.add(
                KnowledgeChunkRecord(
                    document_id=(
                        document_id
                    ),
                    chunk_id=(
                        chunk.chunk_id
                    ),
                    chunk_index=(
                        chunk.chunk_index
                    ),
                    page_number=(
                        chunk.page_number
                    ),
                    content=(
                        chunk.content
                    ),
                    character_count=len(
                        chunk.content
                    ),
                )
            )

        db.flush()

        # -----------------------------------------
        # Generate embeddings and index in FAISS
        # -----------------------------------------

        indexed_count = (
            knowledge_index_service
            .index_chunks(
                chunks=all_chunks
            )
        )

        if indexed_count == 0:
            raise RuntimeError(
                "No knowledge vectors were created."
            )

        document.status = (
            "COMPLETED"
        )

        document.chunk_count = (
            indexed_count
        )

        document.error_message = (
            None
        )

        db.commit()

        db.refresh(
            document
        )

        return {
            "success": True,
            "document":
                document_to_dict(
                    document
                ),
        }

    except Exception as exc:

        db.rollback()

        # Remove any vectors that may have been
        # written before the failure occurred.
        try:
            knowledge_index_service.remove_document(
                document_id
            )
        except Exception:
            pass

        failed_document = (
            KnowledgeDocumentRecord(
                name=name,
                original_filename=(
                    parsed.filename
                ),
                content_type=(
                    parsed.content_type
                ),
                status="FAILED",
                character_count=len(
                    parsed.full_text
                ),
                chunk_count=0,
                error_message=str(
                    exc
                ),
            )
        )

        db.add(
            failed_document
        )

        db.commit()

        raise


def list_knowledge_documents(
    *,
    db: Session,
) -> list[dict[str, Any]]:

    documents = list(
        db.scalars(
            select(
                KnowledgeDocumentRecord
            )
            .order_by(
                KnowledgeDocumentRecord
                .created_at
                .desc(),

                KnowledgeDocumentRecord
                .id
                .desc(),
            )
        ).all()
    )

    return [
        document_to_dict(
            document
        )
        for document
        in documents
    ]


def get_knowledge_document(
    *,
    db: Session,
    document_id: int,
) -> dict[str, Any] | None:

    document = db.get(
        KnowledgeDocumentRecord,
        document_id,
    )

    if document is None:
        return None

    chunks = list(
        db.scalars(
            select(
                KnowledgeChunkRecord
            )
            .where(
                KnowledgeChunkRecord.document_id
                == document_id
            )
            .order_by(
                KnowledgeChunkRecord.chunk_index
                .asc()
            )
        ).all()
    )

    result = (
        document_to_dict(
            document
        )
    )

    result[
        "chunks"
    ] = [
        chunk_to_dict(
            chunk
        )
        for chunk
        in chunks
    ]

    return result


def delete_knowledge_document(
    *,
    db: Session,
    document_id: int,
) -> bool:

    document = db.get(
        KnowledgeDocumentRecord,
        document_id,
    )

    if document is None:
        return False

    # -----------------------------------------
    # Remove knowledge vectors
    # -----------------------------------------

    knowledge_index_service.remove_document(
        document_id
    )

    # -----------------------------------------
    # Delete document.
    #
    # KnowledgeChunkRecord rows should be
    # removed by ON DELETE CASCADE / relationship
    # cascade configured on the models.
    # -----------------------------------------

    db.delete(
        document
    )

    db.commit()

    return True