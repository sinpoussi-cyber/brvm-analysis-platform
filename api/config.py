# ==============================================================================
# CONFIGURATION DE L'API
# ==============================================================================

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """
    Configuration centralisée de l'application
    """
    
    # Application
    APP_NAME: str = "BRVM Analysis Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "aws-1-eu-west-1.pooler.supabase.com")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres.mdibxftmrdrdhwxgqpkq")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "AndPOU#1994")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 heure
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # 30 jours
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://brvm-platform.com",
        "https://www.brvm-platform.com",
        "https://app.brvm-platform.com"
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
