from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "mci-gpt"
    environment: str = "dev"

    # Database
    database_url: str = "postgresql://mci_user:change_me@postgres:5432/cognitive"
    redis_url: str = "redis://redis:6379/0"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "change_me"
    minio_secure: bool = False
    llm_session_output_bucket: str = "llm-session-outputs"

    # JWT
    jwt_secret: str = "change_me_this_is_secret_key_for_jwt_tokens"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 10080  # 7 days

    # Google OAuth
    google_client_id: str = "your-google-client-id.apps.googleusercontent.com"
    google_client_secret: str = "your-google-client-secret"
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # OpenAI (for LLM chat)
    openai_api_key: str = "sk-your-openai-api-key"
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 500

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
