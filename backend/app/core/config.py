from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://sdn:sdn_secret@localhost:5432/sdn_controller"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    MASTER_SECRET: str = "change_this_in_production_min_32_chars!!"
    SUPERADMIN_PASSWORD: str = "change_this_superadmin_password"
    JWT_SECRET: str = "change_this_jwt_secret_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    SUPERADMIN_USERNAME: str = "jinhoadmin"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin"

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("MASTER_SECRET")
    @classmethod
    def validate_master_secret(cls, v: str) -> str:
        if v == "change_this_in_production_min_32_chars!!":
            raise ValueError(
                "MASTER_SECRET must be changed from the default value. "
                "Set MASTER_SECRET env var to a random 32+ char secret."
            )
        return v

    @field_validator("SUPERADMIN_PASSWORD")
    @classmethod
    def validate_superadmin_password(cls, v: str) -> str:
        if v == "change_this_superadmin_password":
            raise ValueError(
                "SUPERADMIN_PASSWORD must be changed from the default value. "
                "Set SUPERADMIN_PASSWORD env var before starting the server."
            )
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


settings = Settings()
