-- Enable pgvector extension for RAG storage
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL,
    section_id INTEGER,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'upload',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Dimension 768 matches common Google text-embedding models; adjust if needed.
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL,
    section_id INTEGER,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(768),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_course_id ON document_chunks(course_id);
CREATE INDEX IF NOT EXISTS idx_documents_course_id ON documents(course_id);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL,
    user_id TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL,
    user_id TEXT,
    role TEXT NOT NULL, -- user | assistant | system
    content TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_course_user ON conversations(course_id, user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
