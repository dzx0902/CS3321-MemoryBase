from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChunkDraft:
    chunk_no: int
    chunk_text: str
    start_line: int
    end_line: int
    token_count: int


def build_chunks(
    raw_text: str,
    *,
    max_chars: int = 800,
    overlap_lines: int = 1,
) -> list[ChunkDraft]:
    lines = raw_text.splitlines() or [raw_text]
    natural_chunks = _line_level_chunks(lines, max_chars=max_chars)
    if natural_chunks:
        return natural_chunks

    chunks: list[ChunkDraft] = []
    index = 0
    chunk_no = 1

    while index < len(lines):
        start_index = index
        current_lines: list[str] = []
        current_length = 0

        while index < len(lines):
            candidate = lines[index]
            extra = len(candidate) + (1 if current_lines else 0)
            if current_lines and current_length + extra > max_chars:
                break
            current_lines.append(candidate)
            current_length += extra
            index += 1

        chunk_text = "\n".join(current_lines).strip()
        if not chunk_text:
            chunk_text = "\n".join(current_lines)

        chunks.append(
            ChunkDraft(
                chunk_no=chunk_no,
                chunk_text=chunk_text,
                start_line=start_index + 1,
                end_line=start_index + len(current_lines),
                token_count=_estimate_token_count(chunk_text),
            )
        )
        chunk_no += 1

        if index >= len(lines):
            break

        index = max(index - overlap_lines, start_index + 1)

    return chunks


def _line_level_chunks(lines: list[str], *, max_chars: int) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    chunk_no = 1
    for index, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        if len(text) > max_chars:
            return []
        chunks.append(
            ChunkDraft(
                chunk_no=chunk_no,
                chunk_text=text,
                start_line=index + 1,
                end_line=index + 1,
                token_count=_estimate_token_count(text),
            )
        )
        chunk_no += 1
    return chunks


def _estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))
