from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.rag.retrieval_service import (
    knowledge_retrieval_service,
)
from app.ai.tools.base import BaseAITool

from app.db_models.knowledge_document import (
    KnowledgeDocumentRecord,
)


class SearchKnowledgeBaseTool(BaseAITool):
    name = "search_knowledge_base"

    description = (
        "Search uploaded knowledge-base documents using semantic "
        "retrieval. Use this for policies, procedures, IAM guidance, "
        "technical documentation, runbooks, troubleshooting guides, "
        "standards, manuals, and other uploaded knowledge. "
        "Do not use it for live system statistics or database counts."
    )

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The question or semantic search query."
                ),
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 8,
                "description": (
                    "Maximum number of relevant chunks to retrieve."
                ),
            },
            "minimum_similarity": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": (
                    "Minimum semantic similarity. Normally use 0.50."
                ),
            },
            "document_id": {
                "type": [
                    "integer",
                    "null",
                ],
                "description": (
                    "Optional document ID. Use null to search the "
                    "entire knowledge base."
                ),
            },
        },
        "required": [
            "query",
            "limit",
            "minimum_similarity",
            "document_id",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        query = str(
            arguments.get(
                "query",
                "",
            )
            or ""
        ).strip()

        if not query:
            raise ValueError(
                "Knowledge search query cannot be empty."
            )

        limit = int(
            arguments.get(
                "limit",
                5,
            )
            or 5
        )
        limit = max(
            1,
            min(
                limit,
                8,
            ),
        )

        minimum_similarity = float(
            arguments.get(
                "minimum_similarity",
                0.50,
            )
            or 0.50
        )

        document_id_value = arguments.get(
            "document_id"
        )

        if isinstance(
            document_id_value,
            str,
        ):
            cleaned_document_id = (
                document_id_value
                .strip()
                .lower()
            )

            if cleaned_document_id in {
                "",
                "null",
                "none",
            }:
                document_id = None
            else:
                try:
                    document_id = int(
                        document_id_value
                    )
                except ValueError:
                    document_id = None

        elif document_id_value is None:
            document_id = None

        else:
            document_id = int(
            document_id_value
        )

        #
        # If a document was explicitly requested,
        # verify that it exists and is indexed.
        #
        if document_id is not None:
            document = db.get(
                KnowledgeDocumentRecord,
                document_id,
            )

            if document is None:
                return {
                    "found": False,
                    "query": query,
                    "documentId": document_id,
                    "resultCount": 0,
                    "sources": [],
                    "message": (
                        f"Knowledge document {document_id} "
                        "does not exist."
                    ),
                }

            if document.status != "COMPLETED":
                return {
                    "found": False,
                    "query": query,
                    "documentId": document_id,
                    "resultCount": 0,
                    "sources": [],
                    "message": (
                        f"Knowledge document {document_id} "
                        f"is currently {document.status}."
                    ),
                }

        return knowledge_retrieval_service.search(
            query=query,
            limit=limit,
            minimum_similarity=minimum_similarity,
            document_id=document_id,
        )


class ListKnowledgeDocumentsTool(BaseAITool):
    name = "list_knowledge_documents"

    description = (
        "List documents currently available in the IdentityAI "
        "knowledge base. Use this when the user asks what documents, "
        "policies, manuals, runbooks, or knowledge sources are "
        "available. Do not use this for searching document content."
    )

    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": [
                    "string",
                    "null",
                ],
                "description": (
                    "Optional document status such as COMPLETED. "
                    "Normally use COMPLETED."
                ),
            },
        },
        "required": [
            "status",
        ],
        "additionalProperties": False,
    }

    def execute(
        self,
        *,
        db: Session,
        arguments: dict[str, Any],
    ) -> Any:

        status_value = arguments.get(
            "status"
        )

        status = (
            str(status_value).strip().upper()
            if status_value
            else None
        )

        query = select(
            KnowledgeDocumentRecord
        )

        if status:
            query = query.where(
                KnowledgeDocumentRecord.status
                == status
            )

        query = query.order_by(
            KnowledgeDocumentRecord.created_at.desc()
        )

        documents = list(
            db.scalars(query).all()
        )

        return {
            "documentCount": len(documents),
            "documents": [
                {
                    "id": document.id,
                    "name": document.name,
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
                    "createdAt": (
                        document.created_at.isoformat()
                        if document.created_at
                        else None
                    ),
                }
                for document in documents
            ],
        }