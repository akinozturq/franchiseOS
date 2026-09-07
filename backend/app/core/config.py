from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List, Optional
from decimal import Decimal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "Franchise Komisyon Sistemi"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    ENVIRONMENT: str = "development"  # "development", "staging", "production"
    DATABASE_URL: str = "postgresql://postgres@localhost:5432/franchise_os"
    
    JWT_SECRET_KEY: str = "super-secret-franchise-os-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    DEFAULT_KDV_RATE: Decimal = Decimal("0.20")
    CORS_ORIGINS: List[str] = ["*"]

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.ENVIRONMENT == "production":
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "super-secret-franchise-os-key-change-in-production":
                raise ValueError(
                    "Production ortamında güvenli bir JWT_SECRET_KEY (.env veya ortam değişkeni) zorunludur!"
                )
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "Production ortamında JWT_SECRET_KEY en az 32 karakter uzunluğunda olmalıdır!"
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "Production ortamında CORS_ORIGINS için wildcard ('*') kullanılamaz. Yetkili domainleri belirtiniz."
                )
        return self

settings = Settings()

