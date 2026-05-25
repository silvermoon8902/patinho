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
    # When true, deposits skip MP entirely: a fake QR is rendered and the
    # next reconcile call auto-approves. Used to unblock end-to-end tests
    # while real MP credentials are pending. Never set in true production.
    MERCADO_PAGO_SIMULATED: bool = False

    API_FOOTBALL_KEY: str = ""
    # api-futebol.com.br token. Replaces api-football for Brazilian
    # championships. Empty during local dev → integration returns no data.
    API_FUTEBOL_KEY: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@patinho.com.br"
    SMTP_FROM_NAME: str = "Patinho"
    SMTP_USE_TLS: bool = True
    APP_URL: str = "http://localhost:5173"
    # Public base used to build shareable invite links and email links.
    # Currently a free duckdns.org subdomain with a Let's Encrypt cert —
    # gives a real HTTPS origin so WhatsApp linkifies invites and the
    # browser shows the padlock. Swap for the real domain once purchased.
    PUBLIC_BASE_URL: str = "https://patinho-test.duckdns.org"
    TERMS_VERSION: str = "v1"
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.05

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
