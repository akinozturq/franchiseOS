from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from decimal import Decimal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "Franchise Komisyon Sistemi"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "postgresql://postgres@localhost:5432/franchise_os"
    
    JWT_SECRET_KEY: str = "super-secret-franchise-os-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    DEFAULT_KDV_RATE: Decimal = Decimal("0.20")

settings = Settings()

