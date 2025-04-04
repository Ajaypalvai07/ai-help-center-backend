from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Help Center"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered help center application"

    # Security
    SECRET_KEY: str = Field(default=os.getenv("SECRET_KEY", "your-secret-key-here"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7)  # 7 days
    ALGORITHM: str = Field(default="HS256")

    # MongoDB
    MONGODB_URL: str = Field(default=os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
    MONGODB_DB_NAME: str = Field(default=os.getenv("MONGODB_DB_NAME", "ai_help_center"))

    # HuggingFace
    HUGGINGFACE_API_KEY: str = Field(default=os.getenv("HUGGINGFACE_API_KEY", ""))
    HUGGINGFACE_MODEL: str = Field(default=os.getenv("HUGGINGFACE_MODEL", "tiiuae/falcon-7b-instruct"))

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings() 