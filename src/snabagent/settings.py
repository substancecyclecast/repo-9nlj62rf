"""Конфигурация приложения через pydantic-settings.

Все секреты — только из `.env` или env-переменных, никогда не в коде.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMName = Literal["fake", "yandex", "gigachat", "llama", "openai"]


class LLMSettings(BaseSettings):
    """Настройки LLM-роутера (env-prefix LLM_)."""

    primary: LLMName = "fake"
    fallback: LLMName = "fake"
    verifier: LLMName = "fake"
    verifier_fallback: LLMName = "fake"
    temperature: float = 0.1
    timeout_sec: int = 45
    max_retries: int = 3

    # YandexGPT
    yc_folder_id: str = ""
    yc_auth_token: SecretStr = SecretStr("")
    yc_llm_model: str = "yandexgpt/latest"
    yc_embedding_model: str = "text-search-doc/latest"

    # GigaChat
    gigachat_auth_key: SecretStr = SecretStr("")
    gigachat_client_id: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2-Pro"
    gigachat_verify_ssl: bool = False

    # Llama
    llama_base_url: str = ""
    llama_api_key: SecretStr = SecretStr("")
    llama_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

    # OpenAI (только dev)
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1"
    enable_openai_in_prod: bool = False

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _verifier_must_differ_in_real_mode(self) -> LLMSettings:
        """Гарантируем, что verifier != primary, когда не FakeLLM (anti-hallucination)."""
        if self.primary != "fake" and self.primary == self.verifier:
            raise ValueError(
                f"LLM_VERIFIER ({self.verifier}) must differ from LLM_PRIMARY ({self.primary}). "
                "Verifier MUST use a different model to catch primary's hallucinations."
            )
        return self


class Settings(BaseSettings):
    app_env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    secret_key: SecretStr = SecretStr("changeme")
    api_key: SecretStr = SecretStr("dev-only-key-change-in-prod")
    service_public_url: str = "http://localhost:8000"
    demo_mode: bool = True

    # DB
    database_url: str = "postgresql+asyncpg://snab:snab_dev_only@postgres:5432/snabagent"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_nsi_collection: str = "nsi"
    qdrant_suppliers_collection: str = "suppliers"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Embeddings
    embedding_backend: Literal["fake", "sentence-transformers", "yandex"] = "fake"
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 384

    # Email
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "agent@demo.snabagent.ru"
    smtp_use_tls: bool = False

    imap_host: str = "mailhog"
    imap_port: int = 1143
    imap_user: str = "agent@demo.snabagent.ru"
    imap_password: SecretStr = SecretStr("")
    imap_use_ssl: bool = False
    imap_poll_interval_sec: int = 30

    demo_email_domain: str = "demo.snabagent.ru"

    # Sourcing / SPARK
    spark_mock_mode: bool = True
    spark_api_key: SecretStr = SecretStr("")
    web_scraper_user_agent: str = "SnabAgentBot/0.1"
    web_scraper_timeout_sec: int = 10
    web_scraper_max_pages: int = 5

    # Regulatory
    regulatory_block_after_tender_published: bool = True
    regulatory_max_unregulated_amount_rub: int = 1_000_000
    regulatory_allowed_categories: list[str] = Field(
        default_factory=lambda: [
            "mro",
            "it",
            "consumables",
            "services",
            "spot_metals",
            "metals",
            "chemistry",
        ]
    )

    # n8n
    n8n_base_url: str = "http://n8n:5678"
    n8n_api_key: SecretStr = SecretStr("")
    n8n_webhook_escalation: str = ""

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_escalation_chat_id: str = ""

    # Streamlit
    streamlit_api_base: str = "http://api:8000"
    streamlit_admin_password: SecretStr = SecretStr("demo")

    # Sentry
    sentry_dsn: str = ""

    # Frontend / CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8501",
        ]
    )
    frontend_url: str = "http://localhost:5173"
    app_base_url: str = "http://localhost:8000"

    # Подмодели
    llm: LLMSettings = LLMSettings()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _prod_requires_real_secrets(self) -> Settings:
        if self.app_env == "prod" and not self.demo_mode:
            if self.secret_key.get_secret_value() == "changeme":
                raise ValueError(
                    "Production secrets not configured: SECRET_KEY is still 'changeme'. "
                    "Set a strong random SECRET_KEY for production."
                )
            if self.api_key.get_secret_value() == "dev-only-key-change-in-prod":
                raise ValueError(
                    "Production secrets not configured: API_KEY is still 'dev-only-key-change-in-prod'. "
                    "Set a strong random API_KEY for production."
                )
            if self.embedding_backend == "fake":
                raise ValueError(
                    "EMBEDDING_BACKEND=fake запрещён в prod. Установите 'sentence-transformers' или 'yandex'."
                )
        return self


settings = Settings()


def get_settings() -> Settings:
    """Точка возврата текущих настроек. Удобно для тестов с monkeypatch."""
    return settings
