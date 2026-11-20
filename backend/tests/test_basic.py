from app.services.chunking import chunk_text
from app.services.guardrails import redact_pii


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_splits_long_text():
    text = ("palabra " * 1200).strip()
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(isinstance(c, str) and c for c in chunks)


def test_redact_pii_email_and_phone():
    text = "Contacto: test@example.com o +34 600 123 456"
    redacted = redact_pii(text)
    assert "test@example.com" not in redacted
    assert "600 123 456" not in redacted
    assert "[email redactado]" in redacted
    assert "[teléfono redactado]" in redacted
