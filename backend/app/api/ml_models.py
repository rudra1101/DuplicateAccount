from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.ml import train_duplicate_model
from app.ai.ml.model_store import load_model
from app.auth import require_permission
from app.database.session import get_db
from app.schemas.training_label import TrainingLabelCreate
from app.services.reviewer_analytics_service import get_reviewer_feedback_analytics
from app.services.training_label_service import (
    create_training_label,
    get_training_label_summary,
    get_training_rows,
)


router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"],
)


@router.post("/labels")
def add_training_label(
    payload: TrainingLabelCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("ml.train")),
):
    try:
        record = create_training_label(
            db=db,
            candidate_id=payload.candidateId,
            label=payload.label,
            reviewer_comment=payload.reviewerComment,
            reviewer_name=payload.reviewerName,
        )
        return {
            "id": record.id,
            "candidateId": record.candidate_id,
            "label": record.label,
            "createdAt": record.created_at.isoformat() if record.created_at else None,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/train")
def train_model(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("ml.train")),
):
    try:
        rows = get_training_rows(db)
        metadata = train_duplicate_model(rows)
        return {"status": "COMPLETED", "model": metadata}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/current")
def get_current_model(
    _user=Depends(require_permission("ml.view")),
):
    stored_model = load_model()
    if stored_model is None:
        return {"available": False, "model": None}
    return {"available": True, "model": stored_model.metadata}


@router.get("/labels/summary")
def get_label_summary(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("ml.view")),
):
    rows = get_training_rows(db)
    duplicate_count = sum(1 for row in rows if row["label"] == "DUPLICATE")
    not_duplicate_count = sum(1 for row in rows if row["label"] == "NOT_DUPLICATE")
    return {
        "totalUsableLabels": len(rows),
        "duplicateLabels": duplicate_count,
        "notDuplicateLabels": not_duplicate_count,
        "minimumRequired": 20,
        "readyForTraining": (
            len(rows) >= 20
            and duplicate_count > 0
            and not_duplicate_count > 0
        ),
    }


@router.get("/analytics/reviewer-feedback")
def reviewer_feedback_analytics(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("ml.analytics.view")),
):
    return get_reviewer_feedback_analytics(db)


@router.get("/dashboard")
def get_ml_dashboard(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("ml.view")),
):
    label_summary = get_training_label_summary(db)
    stored_model = load_model()

    if stored_model is None:
        model_summary = {
            "available": False,
            "modelVersion": None,
            "trainedAt": None,
            "trainingRows": 0,
            "metrics": {
                "accuracy": None,
                "precision": None,
                "recall": None,
                "f1": None,
                "rocAuc": None,
            },
        }
    else:
        metadata = stored_model.metadata or {}
        metrics = metadata.get("metrics", {}) or {}
        model_summary = {
            "available": True,
            "modelVersion": metadata.get("modelVersion"),
            "trainedAt": metadata.get("trainedAt"),
            "trainingRows": metadata.get("trainingRows", 0),
            "metrics": {
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1": metrics.get("f1"),
                "rocAuc": metrics.get("rocAuc"),
            },
        }

    total_labels = label_summary["totalUsableLabels"]
    minimum_required = label_summary["minimumRequired"]
    progress_percentage = min(
        100,
        round((total_labels / minimum_required) * 100, 2)
        if minimum_required > 0
        else 100,
    )

    return {
        "labels": label_summary,
        "progressPercentage": progress_percentage,
        "model": model_summary,
    }
