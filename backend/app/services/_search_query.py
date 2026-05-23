from __future__ import annotations


def build_websearch_query(tokenized_query: str) -> str:
    terms = [term for term in tokenized_query.split() if term]
    return " OR ".join(terms) if terms else tokenized_query
