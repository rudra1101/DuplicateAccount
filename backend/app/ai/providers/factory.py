from app.ai.config import AISettings
from app.ai.providers.base import (
    BaseAIProvider,
)
from app.ai.providers.ollama_provider import (
    OllamaProvider,
)


class AIProviderFactory:
    @staticmethod
    def create(
        settings: AISettings,
    ) -> BaseAIProvider:
        if settings.provider == "ollama":
            return OllamaProvider(
                settings
            )

        raise ValueError(
            "Unsupported AI provider: "
            f"{settings.provider}"
        )