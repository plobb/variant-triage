from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DB_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/variant_triage"
    )
    SECRET_KEY: str = Field(default="change-me-in-production")
    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: str = Field(default="development")

    # JWT settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    ALGORITHM: str = Field(default="HS256")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
