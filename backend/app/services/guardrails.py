import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from app.services.rag import query_course


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s\-()]{7,}\d)\b")
ID_RE = re.compile(r"\b\d{6,12}\b")


@dataclass
class GuardrailResult:
    allowed: bool
    message: str | None = None
    redacted_text: str | None = None


# Simple in-memory quota: max N requests per window per (course_id,user_id)
_REQUESTS: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def check_rate_limit(course_id: int, user_id: str | None, limit: int = 20, window_seconds: int = 3600) -> GuardrailResult:
    key = (str(course_id), str(user_id or "anon"))
    now = time.time()
    q = _REQUESTS[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        return GuardrailResult(False, "Has alcanzado el límite de consultas por hora para este curso. Intenta más tarde.")
    q.append(now)
    return GuardrailResult(True)


def redact_pii(text: str) -> str:
    text = EMAIL_RE.sub("[email redactado]", text or "")
    text = PHONE_RE.sub("[teléfono redactado]", text)
    # Be conservative with generic long numbers to reduce PII leakage; may over-redact.
    # text = ID_RE.sub("[id redactado]", text)
    return text


def is_in_course_scope(course_id: int, message: str, min_score: float = 0.2) -> GuardrailResult:
    """Heuristic: if retrieval returns no reasonably relevant chunks, treat as likely out-of-scope/no material."""
    try:
        results = query_course(course_id=course_id, query=message, top_k=3)
    except Exception:
        # If retrieval fails, allow generation to respond with safe fallback behavior.
        return GuardrailResult(True)
    if not results:
        return GuardrailResult(False, "Esta información no se encuentra en el material del curso. Te sugiero consultar directamente al docente en el foro de dudas.")
    best = max(float(r.get("score") or 0.0) for r in results)
    if best < min_score:
        return GuardrailResult(False, "Esta información no se encuentra en el material del curso. Te sugiero consultar directamente al docente en el foro de dudas.")
    return GuardrailResult(True)


def apply_input_guardrails(course_id: int, user_id: str | None, message: str) -> GuardrailResult:
    rl = check_rate_limit(course_id, user_id)
    if not rl.allowed:
        return rl
    redacted = redact_pii(message)
    scope = is_in_course_scope(course_id, redacted)
    if not scope.allowed:
        return GuardrailResult(False, scope.message, redacted_text=redacted)
    return GuardrailResult(True, redacted_text=redacted)