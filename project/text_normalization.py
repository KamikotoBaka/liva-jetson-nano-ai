from __future__ import annotations

import re


def normalize_phrase(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"[.,!?;:]+", " ", normalized)
    return " ".join(normalized.split())


def normalize_phrase_relaxed(value: str) -> str:
    normalized = normalize_phrase(value)
    tokens = [token for token in normalized.split() if token not in {"the", "a", "an", "please"}]
    return " ".join(tokens)
