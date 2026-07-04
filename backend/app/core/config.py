"""Application configuration.

Settings are read from environment variables (and an optional .env file) so the
service runs out of the box with SQLite while remaining production-ready for
Postgres. No secrets are required for the deterministic agent to operate; if an
LLM key is supplied the agent core upgrades to model-driven planning.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MANDATE_", env_file=".env", extra="ignore")

    # Core
    app_name: str = "Mandate"
    environment: str = "local"  # local | staging | production
    api_v1_prefix: str = "/api/v1"

    # Persistence. SQLite by default; set MANDATE_DATABASE_URL to a Postgres DSN
    # (e.g. postgresql+psycopg://user:pass@host/db) for production.
    database_url: str = "sqlite:///./data/mandate.db"

    # Agent / LLM. When empty, the deterministic policy engine drives the agent.
    llm_provider: str = "deterministic"  # one of: deterministic | anthropic | openai
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "claude-sonnet-4"

    # Treasury policy defaults (organization-level overrides live in the DB).
    base_stablecoin: str = "USDC"
    min_operating_reserve_usd: float = 50_000.0
    idle_yield_threshold_usd: float = 100_000.0
    max_agent_autonomous_transfer_usd: float = 25_000.0

    # External integrations (live mode requires keys; sandbox is the default).
    integration_mode: str = "sandbox"  # sandbox | live

    # --- Bridge.xyz (fiat off-ramp) ---
    bridge_api_base: str = "https://api.bridge.xyz"
    bridge_api_key: str = ""

    # --- Li.Fi (swap aggregator) ---
    lifi_api_base: str = "https://li.quest/v1"
    lifi_api_key: str = ""

    # --- Stellar ---
    stellar_network: str = "testnet"  # testnet | public
    stellar_horizon_url: str = "https://horizon-testnet.stellar.org"
    stellar_soroban_rpc: str = "https://soroban-testnet.stellar.org"
    stellar_signing_key: str = ""  # Secret key for auto-signing (testnet only)
    soroban_contract_id: str = ""  # Deployed Soroban policy contract ID

    # --- Safe (EVM multisig) ---
    safe_tx_service_base: str = "https://safe-transaction-base.safe.global"
    safe_module_address: str = ""  # Deployed Safe module for auto-sign
    safe_signer_key: str = ""  # Private key for co-signer module

    # --- Cowrie (Nigeria off-ramp anchor) ---
    cowrie_api_base: str = "https://api.cowrie.exchange"
    cowrie_api_key: str = ""

    # --- Flutterwave (Africa payments) ---
    flutterwave_api_base: str = "https://api.flutterwave.com/v3"
    flutterwave_secret_key: str = ""

    # --- YellowCard (Africa off-ramp) ---
    yellowcard_api_base: str = "https://api.yellowcard.io/v1"
    yellowcard_api_key: str = ""
    yellowcard_secret_key: str = ""

    # --- Compliance ---
    chainalysis_api_base: str = "https://api.chainalysis.com/api/kyt/v2"
    chainalysis_api_key: str = ""

    # --- Auth (Privy / JWT) ---
    auth_enabled: bool = False  # Set to True for production
    privy_app_id: str = ""
    privy_app_secret: str = ""
    jwt_secret: str = "mandate-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # --- Operations: rate limiting, webhooks, billing ---
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 120

    # Outbound notifications. When empty, deliveries are recorded to the audit
    # outbox in the DB but not sent over the wire (safe for sandbox/demo).
    slack_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Billing — Mandate's revenue model is a take-rate on payment volume plus a
    # flat SaaS platform fee. These power the in-app billing page and invoices.
    billing_take_rate_bps: int = 25  # 0.25% of settled payment volume
    billing_platform_fee_usd: float = 2_000.0  # monthly SaaS platform fee
    billing_currency: str = "USD"

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def stellar_is_mainnet(self) -> bool:
        return self.stellar_network == "public"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
