from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.ai.rag.retrieval_service import (
    knowledge_retrieval_service,
)
from app.database.session import (
    get_db,
)
from app.services.knowledge_service import (
    delete_knowledge_document,
    get_knowledge_document,
    list_knowledge_documents,
    upload_knowledge_document,
)


router = APIRouter(
    prefix="/knowledge",
    tags=[
        "Knowledge Base"
    ],
)


MAX_FILE_SIZE = (
    20
    * 1024
    * 1024
)


@router.post(
    "/upload"
)
async def upload_document(
    file: UploadFile = File(
        ...
    ),

    name: str | None = Form(
        default=None
    ),

    db: Session = Depends(
        get_db
    ),
):
    filename = (
        file.filename
        or ""
    ).strip()

    if not filename:
        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded file must "
                "have a filename."
            ),
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded document is empty."
            ),
        )

    if (
        len(content)
        > MAX_FILE_SIZE
    ):
        raise HTTPException(
            status_code=413,
            detail=(
                "Document exceeds the "
                "20 MB upload limit."
            ),
        )

    try:
        return (
            upload_knowledge_document(
                db=db,
                filename=filename,
                content=content,
                content_type=(
                    file.content_type
                ),
                display_name=name,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process "
                "knowledge document: "
                f"{exc}"
            ),
        ) from exc


@router.get(
    "/documents"
)
def documents(
    db: Session = Depends(
        get_db
    ),
):
    return {
        "documents":
            list_knowledge_documents(
                db=db
            )
    }


@router.get(
    "/documents/{document_id}"
)
def document_details(
    document_id: int,

    db: Session = Depends(
        get_db
    ),
):
    document = (
        get_knowledge_document(
            db=db,
            document_id=(
                document_id
            ),
        )
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Knowledge document "
                "was not found."
            ),
        )

    return document


@router.delete(
    "/documents/{document_id}"
)
def delete_document(
    document_id: int,

    db: Session = Depends(
        get_db
    ),
):
    try:
        deleted = (
            delete_knowledge_document(
                db=db,
                document_id=(
                    document_id
                ),
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to delete "
                "knowledge document: "
                f"{exc}"
            ),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=(
                "Knowledge document "
                "was not found."
            ),
        )

    return {
        "success": True,
        "documentId":
            document_id,
    }


@router.get(
    "/search"
)
def search_knowledge(
    query: str = Query(
        ...,
        min_length=1,
    ),

    limit: int = Query(
        default=5,
        ge=1,
        le=8,
    ),

    minimum_similarity: float = Query(
        default=0.50,
        ge=0,
        le=1,
    ),

    document_id: int | None = Query(
        default=None,
        ge=1,
    ),
):
    return (
        knowledge_retrieval_service
        .search(
            query=query,
            limit=limit,
            minimum_similarity=(
                minimum_similarity
            ),
            document_id=(
                document_id
            ),
        )
    )