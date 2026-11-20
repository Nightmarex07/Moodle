from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "moodle-ai-assistant"
    app_env: str = "development"
    api_key: str = "change-me"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str = "postgresql+psycopg://moodle_ai:moodle_ai_password@db:5432/moodle_ai"
    moodle_base_url: str = ""
    moodle_ws_token: str = ""

    llm_provider: str = "google"
    llm_model: str = "models/gemini-3.8-flash"
    embedding_model: str = "models/gemini-embedding-001"
    embedding_dimensions: int = 768
    openai_api_key: str | None = None
    google_api_key: str | None = None

    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50
    retrieval_top_k: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
