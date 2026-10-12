import os
from typing import List, Optional
from pydantic import model_validator, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(case_sensitive=True)

    PROJECT_NAME: str = "data-quality-auditor-alan-vo"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")

    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data_quality.db")

    # Keycloak OIDC
    OIDC_ISSUER_URL: str = os.getenv(
        "OIDC_ISSUER_URL", "http://127.0.0.1:8080/realms/data-quality-auditor"
    )
    OIDC_AUDIENCE: str = os.getenv("OIDC_AUDIENCE", "data-quality-auditor")
    OIDC_JWKS_URL: Optional[str] = os.getenv("OIDC_JWKS_URL", None)
    JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET", None)

    # Multi-provider LLM configuration (server-side only)
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY", None)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai-compatible")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))

    CORS_ORIGINS: List[str] = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

    @model_validator(mode="after")
    def validate_production_demo(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production" and self.DEMO_MODE:
            raise RuntimeError(
                "FATAL: DEMO_MODE cannot be enabled when ENVIRONMENT is 'production'."
            )
        return self

settings = Settings()
