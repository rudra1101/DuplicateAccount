import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AISettings:
    provider: str
    ollama_base_url: str
    fast_model: str
    reasoning_model: str
    embedding_model: str
    max_tool_iterations: int
    default_timezone: str


def get_ai_settings() -> AISettings:
    raw_max_iterations = os.getenv(
        "AI_MAX_TOOL_ITERATIONS",
        "6",
    )

    try:
        max_tool_iterations = int(
            raw_max_iterations
        )
    except ValueError:
        max_tool_iterations = 6

    return AISettings(
        provider=os.getenv(
            "AI_PROVIDER",
            "ollama",
        ).strip().lower(),
        ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434",
        ).strip(),
        fast_model=os.getenv(
            "AI_FAST_MODEL",
            "llama3.1:8b",
        ).strip(),
        reasoning_model=os.getenv(
            "AI_REASONING_MODEL",
            "llama3.1:8b",
        ).strip(),
        embedding_model=os.getenv(
            "AI_EMBEDDING_MODEL",
            "nomic-embed-text",
        ).strip(),
        max_tool_iterations=max(
            1,
            min(
                max_tool_iterations,
                12,
            ),
        ),
        default_timezone=os.getenv(
            "AI_DEFAULT_TIMEZONE",
            "Asia/Kolkata",
        ).strip(),
    )