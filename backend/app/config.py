from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str = "patinho"
    POSTGRES_PASSWORD: str = "patinho"
    POSTGRES_DB: str = "patinho"
    DATABASE_URL: str = "postgresql+asyncpg://patinho:patinho@localhost:5432/patinho"

    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    MERCADO_PAGO_ACCESS_TOKEN: str = ""
    MERCADO_PAGO_WEBHOOK_SECRET: str = ""
    MERCADO_PAGO_PIX_KEY: str = ""

    API_FOOTBALL_KEY: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
