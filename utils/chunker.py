import re
from enum import Enum
from typing import Protocol


class ChunkingStrategy(str, Enum):

    fixed = "fixed" # sliding character windows with overlap
    sentence = "sentence" # merge whole sentences up to the chunk size (long sentences are split)


class Chunker(Protocol):
    def chunk(self, text: str) -> list[str]: ...


class TextChunker:
    """Fixed-size character windows with overlap (sliding window)."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + self.chunk_size])
            start += self.chunk_size - self.overlap
        return chunks


class SentenceAwareChunker:
    """Groups sentences into chunks up to max_chars"""

    def __init__(self, max_chars: int = 500):
        self.max_chars = max_chars

    @staticmethod
    def _sentences(text: str) -> list[str]:
        if not text or not text.strip():
            return []
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def chunk(self, text: str) -> list[str]:
        sentences = self._sentences(text)
        if not sentences:
            return []
        chunks: list[str] = []
        i = 0
        while i < len(sentences):
            s = sentences[i]
            if len(s) > self.max_chars:
                for start in range(0, len(s), self.max_chars):
                    chunks.append(s[start : start + self.max_chars])
                i += 1
                continue
            group = [s]
            length = len(s)
            i += 1
            while i < len(sentences):
                s = sentences[i]
                add = len(s) + 1
                if length + add > self.max_chars:
                    break
                group.append(s)
                length += add
                i += 1
            chunks.append(" ".join(group))
        return chunks


def get_chunker(
    strategy: str | ChunkingStrategy,
    chunk_size: int = 500,
    overlap: int = 50,
) -> Chunker:
    s = strategy.value if isinstance(strategy, ChunkingStrategy) else strategy.lower().strip()
    if s in ("fixed", "sliding", "fixed_size"):
        return TextChunker(chunk_size, overlap)
    if s in ("sentence", "sentence_aware"):
        return SentenceAwareChunker(max_chars=chunk_size)
    raise ValueError(f"Unknown chunking strategy: {strategy!r}")
