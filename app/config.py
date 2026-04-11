from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ORANGE_CLIENT_ID: str
    ORANGE_CLIENT_SECRET: str
    ORANGE_SENDER_NUMBER: str
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_ADMIN_KEY: str = "change-me-in-production"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    FRONTEND_URL: str = "http://localhost:5173"
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"

settings = Settings()