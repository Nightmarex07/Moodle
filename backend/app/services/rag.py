import json
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from sqlalchemy import text

from app.core.config import settings
from app.core.db import get_db
from app.services.chunking import chunk_text
from app.services.embeddings import embed_query, embed_texts


def extract_text_from_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def ingest_document(
    *,
    course_id: int,
    source_name: str,
    content: str,
    source_type: str = "upload",
    section_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    metadata = metadata or {}
    chunks = chunk_text(content, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
    if not chunks:
        return {"document_id": None, "chunks_stored": 0, "message": "No text extracted"}

    embeddings = embed_texts(chunks)

    with get_db() as db:
        doc_row = db.execute(
            text(
                """
                INSERT INTO documents (course_id, section_id, source_name, source_type, metadata)
                VALUES (:course_id, :section_id, :source_name, :source_type, CAST(:metadata AS jsonb))
                RETURNING id
                """
            ),
            {
                "course_id": course_id,
                "section_id": section_id,
                "source_name": source_name,
                "source_type": source_type,
                "metadata": json.dumps(metadata),
            },
        ).mappings().one()
        document_id = doc_row["id"]

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            db.execute(
                text(
                    """
                    INSERT INTO document_chunks
                        (document_id, course_id, section_id, chunk_index, content, metadata, embedding)
                    VALUES
                        (:document_id, :course_id, :section_id, :chunk_index, :content, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
                    """
                ),
                {
                    "document_id": document_id,
                    "course_id": course_id,
                    "section_id": section_id,
                    "chunk_index": idx,
                    "content": chunk,
                    "metadata": json.dumps(metadata),
                    "embedding": "[" + ",".join(str(x) for x in emb) + "]",
                },
            )

    return {"document_id": document_id, "chunks_stored": len(chunks)}


def query_course(*, course_id: int, query: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or settings.retrieval_top_k
    q_emb = embed_query(query)
    emb_literal = "[" + ",".join(str(x) for x in q_emb) + "]"
    with get_db() as db:
        rows = db.execute(
            text(
                """
                SELECT dc.id, dc.document_id, dc.course_id, dc.section_id, dc.chunk_index, dc.content,
                       dc.metadata, d.source_name,
                       (dc.embedding <=> CAST(:embedding AS vector)) AS distance
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE dc.course_id = :course_id
                ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {"course_id": course_id, "embedding": emb_literal, "limit": top_k},
        ).mappings().all()

    results = []
    for r in rows:
        item = dict(r)
        # distance: lower is closer; convert to a rough similarity score for convenience
        item["score"] = 1.0 / (1.0 + float(item.get("distance") or 0.0))
        results.append(item)
    return results
