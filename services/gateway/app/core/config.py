from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CV Gateway"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_KEY: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # Triton
    TRITON_ENABLED: bool
    TRITON_HOST: str = "triton-service"
    TRITON_PORT: int = 8001
    TRITON_TIMEOUT: int = 10
    TRITON_MAX_CONNECTIONS: int = 10

    # Kafka
    QUEUE_ENABLED: bool
    KAFKA_BOOTSTRAP_SERVERS: str

    # Redis
    REDIS_ENABLED: bool
    REDIS_HOST: str = "redis-service"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_TTL: int = 3600  # 1 hour

    # Stream
    STREAM_ENABLED: bool
    STREAM_ENDPOINT: str
    STREAM_TIMEOUT: int = 10

    # Telemetry
    OTEL_ENABLED: bool
    OTEL_ENDPOINT: str
    TEMPO_ENDPOINT: str

    # Logging
    LOG_LEVEL: str = "INFO"

    # Mock
    TRITON_MOCK: bool
    CACHE_MOCK: bool
    QUEUE_MOCK: bool
    STREAM_MOCK: bool

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
