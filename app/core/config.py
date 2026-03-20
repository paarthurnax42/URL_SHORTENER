from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    LINK_LENGHT: int
    DEFAULT_EXPIRATION_MINUTES: int = 60  # Время жизни ссылки по умолчанию (минуты)

    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 часа

    # CORS settings
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASS: str | None = None

    # Cleanup settings (days)
    UNUSED_LINKS_DAYS: int = 30

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CORS_ORIGINS_LIST(self):
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
