import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import settings
from app.core.db import db_ping, get_db
from app.services.chat import get_history, get_or_create_conversation, stream_chat
from app.services.moodle import MoodleClient
from app.services.rag import extract_text_from_pdf_bytes, ingest_document, query_course

router = APIRouter()


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return x_api_key


def ensure_chat_schema() -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL,
            user_id TEXT,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            course_id INTEGER NOT NULL,
            user_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            citations JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_conversations_course_user ON conversations(course_id, user_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)",
    ]
    with get_db() as db:
        for s in stmts:
            db.execute(text(s))


class IngestTextRequest(BaseModel):
    course_id: int
    section_id: Optional[int] = None
    source_name: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source_type: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    course_id: int
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = None


class ChatRequest(BaseModel):
    course_id: int
    message: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    user_role: str = "student"  # student | teacher
    conversation_id: Optional[int] = None
    stream: bool = True


@router.get("/health")
def health() -> dict:
    db_ok = False
    try:
        db_ok = db_ping()
    except Exception:
        db_ok = False
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env, "db": db_ok}


@router.get("/api/v1/ping")
def ping(_: str = Depends(verify_api_key)) -> dict:
    """Authenticated ping endpoint for Sprint 1 Moodle <-> backend connectivity."""
    return {"status": "ok", "message": "pong"}


@router.post("/api/v1/ingest/text")
def ingest_text(req: IngestTextRequest, _: str = Depends(verify_api_key)) -> dict:
    result = ingest_document(
        course_id=req.course_id,
        section_id=req.section_id,
        source_name=req.source_name,
        content=req.text,
        source_type=req.source_type,
        metadata=req.metadata,
    )
    return {"status": "ok", **result}


@router.post("/api/v1/ingest/pdf")
async def ingest_pdf(
    course_id: int = Form(...),
    source_name: str = Form(...),
    section_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    _: str = Depends(verify_api_key),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        content = extract_text_from_pdf_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {e}")

    result = ingest_document(
        course_id=course_id,
        section_id=section_id,
        source_name=source_name or file.filename or "uploaded.pdf",
        content=content,
        source_type="pdf",
        metadata={"filename": file.filename},
    )
    return {"status": "ok", **result}


@router.post("/api/v1/query")
def query(req: QueryRequest, _: str = Depends(verify_api_key)) -> dict:
    try:
        results = query_course(course_id=req.course_id, query=req.query, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    return {
        "status": "ok",
        "course_id": req.course_id,
        "query": req.query,
        "results": results,
    }


@router.post("/api/v1/moodle/ingest-course")
def ingest_moodle_course(course_id: int, _: str = Depends(verify_api_key)) -> dict:
    """Ingest Moodle course contents: section/module descriptions and supported files (PDF/text)."""
    client = MoodleClient()
    try:
        sections = client.get_course_contents(course_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Moodle fetch failed: {e}")

    ingested = []
    errors = []
    for section in sections or []:
        section_id = section.get("id")
        section_name = section.get("name") or f"section-{section_id}"
        summary = (section.get("summary") or "").strip()
        if summary:
            ingested.append(ingest_document(
                course_id=course_id,
                section_id=section_id,
                source_name=f"{section_name} (summary)",
                content=summary,
                source_type="moodle_section",
                metadata={"section_name": section_name},
            ))
        for mod in section.get("modules", []) or []:
            mod_name = mod.get("name") or "module"
            desc = (mod.get("description") or "").strip()
            if desc:
                ingested.append(ingest_document(
                    course_id=course_id,
                    section_id=section_id,
                    source_name=mod_name,
                    content=desc,
                    source_type="moodle_module",
                    metadata={"module_id": mod.get("id"), "modname": mod.get("modname")},
                ))

            for content_item in mod.get("contents", []) or []:
                if content_item.get("type") != "file":
                    continue
                filename = content_item.get("filename") or mod_name
                fileurl = content_item.get("fileurl")
                mimetype = (content_item.get("mimetype") or "").lower()
                if not fileurl:
                    continue
                try:
                    data = client.download_file(fileurl)
                    text_content = ""
                    source_type = "moodle_file"
                    lower = filename.lower()
                    if mimetype == "application/pdf" or lower.endswith(".pdf"):
                        text_content = extract_text_from_pdf_bytes(data)
                        source_type = "moodle_pdf"
                    elif mimetype.startswith("text/") or lower.endswith((".txt", ".md", ".html", ".htm")):
                        try:
                            text_content = data.decode("utf-8")
                        except Exception:
                            text_content = data.decode("latin-1", errors="ignore")
                        source_type = "moodle_text"
                    else:
                        continue

                    if not (text_content or "").strip():
                        continue
                    ingested.append(ingest_document(
                        course_id=course_id,
                        section_id=section_id,
                        source_name=filename,
                        content=text_content,
                        source_type=source_type,
                        metadata={
                            "module_id": mod.get("id"),
                            "modname": mod.get("modname"),
                            "filename": filename,
                            "mimetype": mimetype,
                        },
                    ))
                except Exception as e:
                    errors.append({"file": filename, "error": str(e)})

    return {
        "status": "ok",
        "course_id": course_id,
        "items_ingested": len(ingested),
        "errors": errors,
        "details": ingested,
    }


@router.post("/api/v1/chat")
def chat(req: ChatRequest, _: str = Depends(verify_api_key)):
    ensure_chat_schema()
    try:
        if req.stream:
            return StreamingResponse(
                stream_chat(
                    course_id=req.course_id,
                    user_id=req.user_id,
                    user_role=req.user_role,
                    message=req.message,
                    conversation_id=req.conversation_id,
                ),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        # Non-stream fallback: collect stream
        chunks = []
        conversation_id = req.conversation_id
        citations = []
        for event in stream_chat(
            course_id=req.course_id,
            user_id=req.user_id,
            user_role=req.user_role,
            message=req.message,
            conversation_id=req.conversation_id,
        ):
            if event.startswith("event: meta"):
                data = json.loads(event.split("data: ", 1)[1].strip())
                conversation_id = data.get("conversation_id", conversation_id)
                citations = data.get("citations", [])
            elif event.startswith("event: token"):
                data = json.loads(event.split("data: ", 1)[1].strip())
                chunks.append(data.get("text", ""))
        return {"status": "ok", "conversation_id": conversation_id, "answer": "".join(chunks), "citations": citations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@router.get("/api/v1/history")
def history(course_id: int, user_id: Optional[str] = None, _: str = Depends(verify_api_key)) -> dict:
    ensure_chat_schema()
    with get_db() as db:
        conv = db.execute(
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
        if not conv:
            return {"status": "ok", "conversation_id": None, "messages": []}
        cid = int(conv["id"])
    msgs = get_history(cid, limit=50)
    # created_at may be non-serializable; stringify
    for m in msgs:
        if m.get("created_at") is not None:
            m["created_at"] = str(m["created_at"])
    return {"status": "ok", "conversation_id": cid, "messages": msgs}
