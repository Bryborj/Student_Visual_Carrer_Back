from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql://postgres:devpassword@localhost:5433/forobuap_dev"
    POSTGRES: str | None = None  # Soporte legado para la variable usada en el proyecto original

    # Security & Admin
    # En producción (DEV_MODE=false) ADMIN_PASSWORD y JWT_SECRET son obligatorias; en desarrollo se usan valores seguros locales.
    ADMIN_PASSWORD: str | None = None
    ADMIN_NOTIFICATION_EMAIL: str = "community@forobuap.zrootsh.com"
    DISABLE_DEV_PIN: bool = False
    DEV_MODE: bool = False

    # JWT Authentication
    JWT_SECRET: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días de validez

    # CORS: orígenes permitidos separados por comas
    CORS_ORIGINS: str = "http://localhost:5400,http://localhost:5173"

    # Resend Email Configuration
    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str = "community@forobuap.zrootsh.com"
    RESEND_FROM_NAME: str = "Foro Comunidad BUAP 🐺"

    # Hunter API (Email verification)
    emailVerifierURL: str | None = "https://api.hunter.io/v2/email-verifier"
    emailVerifierKey: str | None = None

    # Server Configuration
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # Community Governance & Voting Thresholds
    VOTE_WINDOW_DAYS: int = 7
    AUTO_APPROVE_MIN_VOTES: int = 10
    AUTO_APPROVE_RATIO: float = 0.51  # Más del 50% de los usuarios registrados

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if not self.ADMIN_PASSWORD:
            if not self.DEV_MODE:
                raise ValueError(
                    "ADMIN_PASSWORD es obligatoria cuando DEV_MODE=false. "
                    "Defínela en el entorno o en .env."
                )
            self.ADMIN_PASSWORD = "admin-dev"

        if not self.JWT_SECRET:
            if not self.DEV_MODE:
                raise ValueError(
                    "JWT_SECRET es obligatoria cuando DEV_MODE=false. "
                    "Defínela en el entorno o en .env."
                )
            self.JWT_SECRET = "dev-jwt-secret-key-buap-visual-carrer-local-dev-only"

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def get_database_url(self) -> str:
        # Prioridad: DATABASE_URL definida explícitamente > POSTGRES (legado) > valor por defecto local.
        if "DATABASE_URL" in self.model_fields_set:
            raw = self.DATABASE_URL
        else:
            raw = self.POSTGRES or self.DATABASE_URL
        # Limpiar comillas accidentales
        clean = raw.strip().strip("'\"")
        # Asegurar protocolo postgresql://
        if clean.startswith("postgres://"):
            clean = clean.replace("postgres://", "postgresql://", 1)
        return clean


settings = Settings()
