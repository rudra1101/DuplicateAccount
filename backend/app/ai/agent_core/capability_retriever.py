from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz.fuzz import token_set_ratio


_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(value: Any) -> set[str]:
    return set(_WORD_RE.findall(str(value or "").casefold()))


def _schema_text(parameters: dict[str, Any] | None) -> str:
    if not isinstance(parameters, dict):
        return ""
    properties = parameters.get("properties")
    if not isinstance(properties, dict):
        return ""

    parts: list[str] = []
    for name, definition in properties.items():
        parts.append(str(name).replace("_", " "))
        if isinstance(definition, dict):
            description = definition.get("description")
            if description:
                parts.append(str(description))
            enum = definition.get("enum")
            if isinstance(enum, list):
                parts.extend(str(item) for item in enum if item is not None)
    return " ".join(parts)


def _definition_document(definition: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            str(definition.get("name") or "").replace("_", " "),
            str(definition.get("description") or ""),
            _schema_text(definition.get("parameters")),
        )
        if part
    )


@dataclass(frozen=True)
class RankedCapability:
    definition: dict[str, Any]
    score: float


class CapabilityRetriever:
    """Retrieve the most relevant authorized tools without phrase routing.

    Rudrix can have dozens of capabilities. Sending every schema to a small local
    model makes native tool selection less reliable. This retriever uses the tool
    contracts themselves as the searchable corpus, so new capabilities become
    discoverable by registering a well-described tool rather than adding keyword
    branches to the chatbot runtime.
    """

    def __init__(self, definitions: list[dict[str, Any]]) -> None:
        self._definitions = list(definitions)

    def rank(self, query: str) -> list[RankedCapability]:
        query_text = str(query or "").strip()
        query_words = _words(query_text)
        ranked: list[RankedCapability] = []

        for definition in self._definitions:
            document = _definition_document(definition)
            document_words = _words(document)
            overlap = len(query_words & document_words)
            coverage = overlap / max(1, len(query_words))
            fuzzy = token_set_ratio(query_text, document) / 100.0 if query_text else 0.0
            name_words = _words(str(definition.get("name") or "").replace("_", " "))
            name_overlap = len(query_words & name_words)

            score = (coverage * 0.55) + (fuzzy * 0.30) + (name_overlap * 0.15)
            ranked.append(RankedCapability(definition=definition, score=score))

        return sorted(ranked, key=lambda item: item.score, reverse=True)

    def select(
        self,
        query: str,
        *,
        limit: int = 8,
        always_include: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._definitions:
            return []

        ranked = self.rank(query)
        selected: list[dict[str, Any]] = []
        seen: set[str] = set()

        for item in ranked[: max(1, limit)]:
            name = str(item.definition.get("name") or "")
            if not name or name in seen:
                continue
            selected.append(item.definition)
            seen.add(name)

        for definition in self._definitions:
            name = str(definition.get("name") or "")
            if name in (always_include or set()) and name not in seen:
                selected.append(definition)
                seen.add(name)

        return selected
