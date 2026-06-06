"""
Application configuration settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # TF-Rack Connection
    TF_RACK_IP: str = "192.168.1.100"
    TF_RACK_PORT: int = 49280
    TF_RACK_RECONNECT_INTERVAL: int = 5

    # Dante Configuration
    DANTE_DISCOVERY_ENABLED: bool = True
    DANTE_NETWORK_INTERFACE: Optional[str] = None

    # E-ink Display Configuration
    EINK_ENABLED: bool = True
    EINK_REFRESH_INTERVAL: int = 300  # seconds
    EINK_DISPLAY_COUNT: int = 16  # Number of e-ink displays

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/showbuilder.db"

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # API Settings
    API_PREFIX: str = "/api"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
