from __future__ import annotations

from collections import OrderedDict
from threading import RLock


class EmbeddingCache:
    """
    Thread-safe bounded in-memory LRU cache.

    This is suitable for local development and a
    single-process deployment. Later, it can be replaced
    with Redis or PostgreSQL without changing the
    duplicate engine.
    """

    def __init__(
        self,
        max_size: int = 10_000,
    ) -> None:
        if max_size < 1:
            raise ValueError(
                "Embedding cache max_size must be at least 1."
            )

        self._max_size = max_size
        self._values: OrderedDict[
            str,
            list[float],
        ] = OrderedDict()

        self._lock = RLock()

    def get(
        self,
        key: str,
    ) -> list[float] | None:
        with self._lock:
            value = self._values.get(key)

            if value is None:
                return None

            self._values.move_to_end(key)

            # Return a copy so callers cannot mutate
            # the cached vector.
            return list(value)

    def set(
        self,
        key: str,
        value: list[float],
    ) -> None:
        with self._lock:
            self._values[key] = list(value)
            self._values.move_to_end(key)

            while (
                len(self._values)
                > self._max_size
            ):
                self._values.popitem(
                    last=False
                )

    def clear(self) -> None:
        with self._lock:
            self._values.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._values)