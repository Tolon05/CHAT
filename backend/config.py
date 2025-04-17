import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./app.db")
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "some_secret_key"))
    SESSION_SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SESSION_SECRET_KEY", "some_secret_key"))
    EMAIL: str = Field(default_factory=lambda: os.getenv("EMAIL"))
    EMAIL_PASSWORD: str = Field(default_factory=lambda: os.getenv("EMAIL_PASSWORD"))
    
    REDIS_HOST: str = Field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT: int = Field(default_factory=lambda: int(os.getenv("REDIS_PORT", 6379)))
    REDIS_PASSWORD: str = Field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))
    
    CELERY_BROKER_URL: str = Field(
        default_factory=lambda: os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    )
    CELERY_BACKEND_URL: str = Field(
        default_factory=lambda: os.getenv("CELERY_BACKEND_URL", "redis://localhost:6379/1")
    )
    CELERY_TOKENS_URL: str = Field(
        default_factory=lambda: os.getenv("CELERY_TOKENS_URL", "redis://localhost:6379/2")
    )

    class Config:
        env_file = ".env"

settings = Settings()
