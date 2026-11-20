from typing import Sequence
import google.generativeai as genai

from app.core.config import settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    genai.configure(api_key=settings.google_api_key)
    _configured = True


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    _ensure_configured()
    vectors: list[list[float]] = []
    model = settings.embedding_model or "models/gemini-embedding-001"
    for text in texts:
        kwargs = {"model": model, "content": text, "task_type": "retrieval_document"}
        if settings.embedding_dimensions:
            kwargs["output_dimensionality"] = settings.embedding_dimensions
        result = genai.embed_content(**kwargs)
        emb = result.get("embedding") if isinstance(result, dict) else getattr(result, "embedding", None)
        if emb is None:
            raise RuntimeError("Embedding response missing 'embedding'")
        vectors.append(list(emb))
    return vectors


def embed_query(text: str) -> list[float]:
    _ensure_configured()
    model = settings.embedding_model or "models/gemini-embedding-001"
    kwargs = {"model": model, "content": text, "task_type": "retrieval_query"}
    if settings.embedding_dimensions:
        kwargs["output_dimensionality"] = settings.embedding_dimensions
    result = genai.embed_content(**kwargs)
    emb = result.get("embedding") if isinstance(result, dict) else getattr(result, "embedding", None)
    if emb is None:
        raise RuntimeError("Embedding response missing 'embedding'")
    return list(emb)
