import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/forobuap_dev"
    POSTGRES: str | None = None  # Soporte para la variable usada en el proyecto original

    # Security & Admin
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_NOTIFICATION_EMAIL: str = "community@forobuap.zrootsh.com"
    DISABLE_DEV_PIN: bool = False
    DEV_MODE: bool = False

    # Resend Email Configuration
    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str = "community@forobuap.zrootsh.com"
    RESEND_FROM_NAME: str = "Foro Comunidad BUAP 🐺"

    # Hunter API (Email verification)
    emailVerifierURL: str | None = "https://api.hunter.io/v2/email-verifier"
    emailVerifierKey: str | None = None

    # Server Configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Community Governance & Voting Thresholds
    VOTE_WINDOW_DAYS: int = 7
    AUTO_APPROVE_MIN_VOTES: int = 10
    AUTO_APPROVE_RATIO: float = 0.51  # Más del 50% de los usuarios registrados

    def get_database_url(self) -> str:
        # Priorizar POSTGRES si existe (del .env original) o DATABASE_URL
        raw = self.POSTGRES or self.DATABASE_URL
        # Limpiar comillas accidentales
        clean = raw.strip().strip("'\"")
        # Asegurar protocolo asyncpg si es necesario o postgresql://
        if clean.startswith("postgres://"):
            clean = clean.replace("postgres://", "postgresql://", 1)
        return clean

settings = Settings()
