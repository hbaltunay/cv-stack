from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_CONSUMER_GROUP_ID: str = "cv-inference-consumer"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_MAX_POLL_INTERVAL_MS: int = 300_000
    KAFKA_SESSION_TIMEOUT_MS: int = 30_000
    KAFKA_HEARTBEAT_INTERVAL_MS: int = 10_000

    # Topic
    KAFKA_TOPIC_NAME: str = "infer-topic"
    # KAFKA_TOPIC_dlq: str = "dead-letter-queue"
    KAFKA_DLQ_MAX_RETRIES: int = 3

    # Triton
    TRITON_HOST: str = "triton-service"
    TRITON_PORT: int = 8001
    TRITON_TIMEOUT: int = 10
    TRITON_MAX_CONNECTIONS: int = 10

    # Redis
    REDIS_HOST: str = "redis-service"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_TTL: int = 3600  # 1 hour

    # Telemetry
    OTEL_ENABLED: bool
    OTEL_ENDPOINT: str

    # JWT
    SERVICE_SECRET_KEY: str
    SERVICE_NAME: str

    # General
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "test"

    # Mock
    CACHE_MOCK: bool = True
    TRITON_MOCK: bool = True

    # Consumers
    CONSUMER_TYPE: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
