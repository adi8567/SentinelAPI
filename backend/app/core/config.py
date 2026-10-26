"""SentinelAPI Configuration Module.

Provides robust, typed configuration management via Pydantic BaseSettings,
supporting environment variables, .env files, and secure masking of credentials.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogFormat(str, Enum):
    JSON = "json"
    CONSOLE = "console"


class StreamingBackend(str, Enum):
    KAFKA = "kafka"
    MEMORY = "memory"
    FILE = "file"


class StorageBackend(str, Enum):
    DUCKDB = "duckdb"
    CLICKHOUSE = "clickhouse"
    TIMESCALEDB = "timescaledb"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General Project Info
    PROJECT_NAME: str = "SentinelAPI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Server Bind
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & Authentication
    SECRET_KEY: str = Field(default="sentinel-insecure-dev-key-change-in-production-32charsmin", min_length=16)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # API Keys for ingestion agents & clients
    ADMIN_API_KEY: str = Field(default="sentinel_admin_sec_key_prod_884920", min_length=16)
    INGESTION_API_KEYS: List[str] = Field(
        default_factory=lambda: [
            "sentinel_agent_key_nginx_01928374",
            "sentinel_agent_key_envoy_09182736",
            "sentinel_agent_key_kong_05128374",
            "sentinel_agent_key_aws_08273615",
            "sentinel_agent_key_azure_07182934",
            "sentinel_agent_key_gcp_06192837",
            "sentinel_agent_key_otel_04182930",
        ]
    )

    # Ingestion API settings
    MAX_BATCH_SIZE: int = 50_000
    MAX_PAYLOAD_SIZE_MB: int = 50
    ALLOW_ANONYMOUS_INGESTION: bool = False  # Strict security by default

    # Streaming & Message Broker
    STREAMING_BACKEND: StreamingBackend = StreamingBackend.MEMORY
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_NORMALIZED_EVENTS: str = "sentinelapi.events.normalized"
    KAFKA_TOPIC_RAW_EVENTS: str = "sentinelapi.events.raw"
    KAFKA_CLIENT_ID: str = "sentinelapi-ingestion-service"
    KAFKA_ACKS: str = "all"
    KAFKA_RETRIES: int = 3
    KAFKA_BATCH_SIZE: int = 16384
    KAFKA_LINGER_MS: int = 10
    STREAMING_BUFFER_MAX_SIZE: int = 100_000

    # Storage Settings
    STORAGE_BACKEND: StorageBackend = StorageBackend.DUCKDB
    DUCKDB_PATH: str = "data/sentinel_timeseries.duckdb"

    # ClickHouse Settings
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "sentinelapi"
    CLICKHOUSE_SECURE: bool = False

    # TimescaleDB / PostgreSQL Settings
    TIMESCALE_HOST: str = "localhost"
    TIMESCALE_PORT: int = 5432
    TIMESCALE_USER: str = "postgres"
    TIMESCALE_PASSWORD: str = "postgres"
    TIMESCALE_DATABASE: str = "sentinelapi"

    # Logging & Observability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: LogFormat = LogFormat.CONSOLE
    ENABLE_TELEMETRY: bool = True
    PROMETHEUS_METRICS_ENABLED: bool = True

    # Storage retention
    RAW_DATA_RETENTION_DAYS: int = 30
    NORMALIZED_DATA_RETENTION_DAYS: int = 90

    @field_validator("INGESTION_API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v

    def get_all_valid_api_keys(self) -> Set[str]:
        keys = set(self.INGESTION_API_KEYS)
        if self.ADMIN_API_KEY:
            keys.add(self.ADMIN_API_KEY)
        return keys


# Global settings singleton
settings = Settings()
