# -*- coding: utf-8 -*-
"""Test settings for URL shortener application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from tests directory
TESTS_DIR = Path(__file__).parent
load_dotenv(TESTS_DIR / ".env")


class TestSettings:
    """Test environment settings using os.getenv() pattern."""

    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5433"))
    DB_USER: str = os.getenv("DB_USER", "test_user")
    DB_PASS: str = os.getenv("DB_PASS", "test_password")
    DB_NAME: str = os.getenv("DB_NAME", "test_url_shortener")

    # App settings
    LINK_LENGHT: int = int(os.getenv("LINK_LENGHT", "6"))
    DEFAULT_EXPIRATION_MINUTES: int = int(os.getenv("DEFAULT_EXPIRATION_MINUTES", "60"))

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "test-secret-key-for-testing-only")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # CORS settings
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6380"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASS: str | None = os.getenv("REDIS_PASS")

    # Cleanup settings
    UNUSED_LINKS_DAYS: int = int(os.getenv("UNUSED_LINKS_DAYS", "30"))

    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Create test settings instance
test_settings = TestSettings()
