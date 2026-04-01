from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # App
    APP_NAME: str = "WhatsChat AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:Robina123@localhost:5432/whatsapp_db"
    BASE_URL: str = "https://api.rajacloud.online"

    # JWT
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    # WhatsApp
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["https://rajacloud.online", "https://www.rajacloud.online", "https://api.rajacloud.online"]

    class Config:
        env_file = ".env"


settings = Settings()