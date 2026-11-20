import json
from typing import Any, Generator, Iterable

import google.generativeai as genai
from sqlalchemy import text

from app.core.config import settings
from app.core.db import get_db
from app.services.guardrails import apply_input_guardrails, redact_pii
from app.services.rag import query_course

_configured = False


def _ensure_genai() -> None:
    global _configured
    if _configured:
        return
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    genai.configure(api_key=settings.google_api_key)
    _configured = True


def _system_prompt(user_role: str) -> str:
    if (user_role or "").lower() == "teacher":
        mode = "Actúa como asistente analítico para docentes: ofrece resúmenes, análisis y sugerencias pedagógicas basadas en el material del curso."
    else:
        mode = "Actúa como tutor socrático para estudiantes: guía con preguntas, pistas y explicaciones claras sin dar simplemente la respuesta final cuando sea apropiado."
    return (
        "Eres un asistente IA integrado en Moodle. "
        f"{mode} "
        "Responde únicamente con base en el contexto proporcionado del curso. "
        "Si la información no está en el contexto, responde exactamente: "
        "'Esta información no se encuentra en el material del curso. Te sugiero consultar directamente al docente en el foro de dudas'. "
        "Cuando uses información del contexto, incluye citas explícitas al final o en línea con el formato: [Fuente: <source_name>]. "
        "No inventes fuentes ni información."
    )


def get_or_create_conversation(course_id: int, user_id: str | None, user_role: str = "student") -> int:
    with get_db() as db:
        row = db.execute(
            text(
                """
                SELECT id FROM conversations
                WHERE course_id = :course_id
                  AND ((CAST(:user_id AS TEXT) IS NULL AND user_id IS NULL) OR user_id = CAST(:user_id AS TEXT))
                ORDER BY updated_at DESC LIMIT 1
                """
            ),
            {"course_id": course_id, "user_id": user_id},
        ).mappings().first()
        if row:
            return int(row["id"])
        row = db.execute(
            text(
                """
                INSERT INTO conversations (course_id, user_id, role)
                VALUES (:course_id, :user_id, :role)
                RETURNING id
                """
            ),
            {"course_id": course_id, "user_id": user_id, "role": user_role},
        ).mappings().one()
        return int(row["id"])


def get_history(conversation_id: int, limit: int = 20) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            text(
                """
                SELECT role, content, citations, created_at
                FROM messages
                WHERE conversation_id = :cid
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"cid": conversation_id, "limit": limit},
        ).mappings().all()
    return [dict(r) for r in reversed(rows)]


def save_message(conversation_id: int, course_id: int, user_id: str | None, role: str, content: str, citations: list[dict] | None = None) -> None:
    citations = citations or []
    with get_db() as db:
        db.execute(
            text(
                """
                INSERT INTO messages (conversation_id, course_id, user_id, role, content, citations)
                VALUES (:conversation_id, :course_id, :user_id, :role, :content, CAST(:citations AS jsonb))
                """
            ),
            {
                "conversation_id": conversation_id,
                "course_id": course_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "citations": json.dumps(citations),
            },
        )
        db.execute(text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"), {"id": conversation_id})


def build_context_and_citations(course_id: int, query: str) -> tuple[str, list[dict]]:
    results = query_course(course_id=course_id, query=query)
    if not results:
        return "", []
    context_parts = []
    citations = []
    seen = set()
    for r in results:
        src = r.get("source_name") or "Fuente"
        key = (src, r.get("chunk_index"))
        if key not in seen:
            seen.add(key)
            citations.append({
                "source_name": src,
                "document_id": r.get("document_id"),
                "chunk_index": r.get("chunk_index"),
                "section_id": r.get("section_id"),
                "score": r.get("score"),
            })
        context_parts.append(f"[Fuente: {src}]\n{r.get('content','')}")
    return "\n\n---\n\n".join(context_parts), citations


def stream_chat(*, course_id: int, user_id: str | None, user_role: str, message: str, conversation_id: int | None = None) -> Generator[str, None, None]:
    _ensure_genai()
    if conversation_id is None:
        conversation_id = get_or_create_conversation(course_id, user_id, user_role)

    guard = apply_input_guardrails(course_id, user_id, message)
    safe_message = guard.redacted_text or redact_pii(message)

    # Send initial metadata event
    yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id, 'citations': []}, ensure_ascii=False)}\n\n"

    if not guard.allowed:
        answer = guard.message or "Solicitud bloqueada por políticas de seguridad."
        save_message(conversation_id, course_id, user_id, "user", safe_message)
        save_message(conversation_id, course_id, user_id, "assistant", answer, citations=[])
        yield f"event: token\ndata: {json.dumps({'text': answer}, ensure_ascii=False)}\n\n"
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
        return

    history = get_history(conversation_id, limit=10)
    context, citations = build_context_and_citations(course_id, safe_message)
    system = _system_prompt(user_role)

    # Update meta with citations once known
    yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id, 'citations': citations}, ensure_ascii=False)}\n\n"

    prompt = (
        f"{system}\n\n"
        f"Contexto del curso (course_id={course_id}):\n{context if context else '[Sin contexto recuperado]'}\n\n"
        "Historial reciente:\n"
    )
    for h in history:
        prompt += f"{h['role']}: {h['content']}\n"
    prompt += f"user: {safe_message}\nassistant:"

    save_message(conversation_id, course_id, user_id, "user", safe_message)

    model = genai.GenerativeModel(settings.llm_model or "gemini-1.5-flash")
    full_text = ""
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            text_part = getattr(chunk, "text", None) or ""
            if text_part:
                full_text += text_part
                yield f"event: token\ndata: {json.dumps({'text': text_part}, ensure_ascii=False)}\n\n"
    except Exception as e:
        err = f"Error generando respuesta: {e}"
        full_text = err
        yield f"event: error\ndata: {json.dumps({'message': err}, ensure_ascii=False)}\n\n"

    save_message(conversation_id, course_id, user_id, "assistant", full_text, citations=citations)
    yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
