"""Application configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/arinar_local"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    
    # OpenRouter
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout: int = 120
    openrouter_max_retries: int = 2
    
    # Supabase Auth
    supabase_jwt_secret: str = "your-jwt-secret-here"
    supabase_url: str = "http://localhost:54321"
    supabase_project_ref: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    require_auth: bool = True
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "arinar-materials"
    minio_secure: bool = False


settings = Settings()
