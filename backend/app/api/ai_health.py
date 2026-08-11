from fastapi import APIRouter
from fastapi import HTTPException

from ollama import Client

from app.ai.config import (
    get_ai_settings,
)


router = APIRouter(
    prefix="/ai/health",
    tags=["AI"],
)


@router.get("/")
def ai_health():
    settings = get_ai_settings()

    client = Client(
        host=settings.ollama_base_url
    )

    try:
        response = client.list()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama is unavailable: "
                f"{exc}"
            ),
        ) from exc

    installed_models = [
        model.model
        for model in response.models
    ]

    required_models = [
        settings.fast_model,
        settings.embedding_model,
    ]

    missing_models = [
        model
        for model in required_models
        if model not in installed_models
    ]

    return {
        "status": (
            "healthy"
            if not missing_models
            else "degraded"
        ),
        "provider": settings.provider,
        "ollamaBaseUrl": (
            settings.ollama_base_url
        ),
        "chatModel": settings.fast_model,
        "reasoningModel": (
            settings.reasoning_model
        ),
        "embeddingModel": (
            settings.embedding_model
        ),
        "installedModels": (
            installed_models
        ),
        "missingModels": (
            missing_models
        ),
    }