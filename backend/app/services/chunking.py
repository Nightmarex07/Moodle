from typing import Iterable
import tiktoken


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    try:
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        chunks: list[str] = []
        start = 0
        step = max(1, chunk_size - max(0, overlap))
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk = enc.decode(tokens[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            if end == len(tokens):
                break
            start += step
        return chunks
    except Exception:
        # Fallback simple character-based chunking if tokenizer unavailable.
        approx = chunk_size * 4
        ov = overlap * 4
        chunks = []
        i = 0
        while i < len(text):
            part = text[i:i + approx].strip()
            if part:
                chunks.append(part)
            i += max(1, approx - ov)
        return chunks
