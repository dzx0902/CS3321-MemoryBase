from __future__ import annotations

import logging
import re

import jieba

jieba.setLogLevel(logging.WARNING)

TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


def build_search_text(*parts: str | None) -> str:
    text = " ".join(part for part in parts if part)
    tokens: list[str] = []
    for segment in jieba.cut_for_search(text):
        for token in TOKEN_PATTERN.findall(segment):
            # Lowercase normalization matches PostgreSQL simple FTS case folding.
            normalized = token.strip().lower()
            if normalized:
                tokens.append(normalized)
    return " ".join(tokens)
