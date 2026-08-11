from __future__ import annotations

import hashlib

from ollama import Client
from ollama import ResponseError

from app.ai.config import (
    AISettings,
    get_ai_settings,
)
from app.ai.embeddings.cache import (
    EmbeddingCache,
)


class EmbeddingService:
    def __init__(
        self,
        settings: AISettings | None = None,
        cache: EmbeddingCache | None = None,
        batch_size: int = 32,
    ) -> None:
        self._settings = (
            settings
            or get_ai_settings()
        )

        self._client = Client(
            host=self._settings.ollama_base_url
        )

        self._model = (
            self._settings.embedding_model
        )

        self._cache = (
            cache
            or EmbeddingCache()
        )

        self._batch_size = max(
            1,
            batch_size,
        )

    @property
    def model(self) -> str:
        return self._model

    @staticmethod
    def normalize_input(
        text: str,
    ) -> str:
        if text is None:
            return ""

        return " ".join(
            str(text).strip().split()
        )

    def build_cache_key(
        self,
        text: str,
    ) -> str:
        payload = (
            f"{self._model}\n{text}"
        ).encode("utf-8")

        return hashlib.sha256(
            payload
        ).hexdigest()

    def embed(
        self,
        text: str,
    ) -> list[float]:
        vectors = self.embed_many(
            [text]
        )

        if not vectors:
            return []

        return vectors[0]

    def _generate_batch(
        self,
        batch: list[str],
    ) -> list[list[float]]:
        try:
            response = self._client.embed(
                model=self._model,
                input=batch,
            )

        except ResponseError as exc:
            raise RuntimeError(
                "Ollama embedding request failed: "
                f"{exc.error}"
            ) from exc

        except Exception as exc:
            raise RuntimeError(
                "Unable to generate embeddings. "
                "Confirm Ollama is running and "
                f"the model '{self._model}' "
                "is installed."
            ) from exc

        vectors = [
            list(vector)
            for vector in response.embeddings
        ]

        if len(vectors) != len(batch):
            raise RuntimeError(
                "Ollama returned an unexpected "
                "number of embedding vectors. "
                f"Expected {len(batch)}, "
                f"received {len(vectors)}."
            )

        return vectors

    def embed_many(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        normalized_texts = [
            self.normalize_input(text)
            for text in texts
        ]

        results: list[
            list[float] | None
        ] = [
            None
            for _ in normalized_texts
        ]

        missing_texts: list[str] = []
        missing_indexes: list[int] = []

        for index, text in enumerate(
            normalized_texts
        ):
            if not text:
                results[index] = []
                continue

            cache_key = (
                self.build_cache_key(
                    text
                )
            )

            cached_vector = (
                self._cache.get(
                    cache_key
                )
            )

            if cached_vector is not None:
                results[index] = (
                    cached_vector
                )
                continue

            missing_texts.append(
                text
            )

            missing_indexes.append(
                index
            )

        generated_vectors: list[
            list[float]
        ] = []

        for start_index in range(
            0,
            len(missing_texts),
            self._batch_size,
        ):
            batch = missing_texts[
                start_index:
                start_index
                + self._batch_size
            ]

            batch_vectors = (
                self._generate_batch(
                    batch
                )
            )

            generated_vectors.extend(
                batch_vectors
            )

        if (
            len(generated_vectors)
            != len(missing_texts)
        ):
            raise RuntimeError(
                "The total number of generated "
                "embedding vectors does not match "
                "the number of missing inputs."
            )

        for (
            result_index,
            source_text,
            vector,
        ) in zip(
            missing_indexes,
            missing_texts,
            generated_vectors,
            strict=True,
        ):
            results[
                result_index
            ] = vector

            self._cache.set(
                self.build_cache_key(
                    source_text
                ),
                vector,
            )

        return [
            vector
            if vector is not None
            else []
            for vector in results
        ]

    def cache_size(self) -> int:
        return self._cache.size()

    def clear_cache(self) -> None:
        self._cache.clear()


embedding_service = EmbeddingService(
    batch_size=32
)