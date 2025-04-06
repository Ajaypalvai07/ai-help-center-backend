from typing import List
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class Settings:
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Assistant API"
    
    # Environment settings
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "production")

    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "ai_assistance")

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Hugging Face settings
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
    HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "google/flan-t5-base")
    USE_HUGGINGFACE: bool = bool(os.getenv("USE_HUGGINGFACE", "false").lower() == "true")

    # CORS settings
    DEFAULT_CORS_ORIGINS: List[str] = [
        "https://ai-help-center-frontend-vkp9.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173"
    ]

    def validate_settings(self) -> None:
        """Validate required settings are properly configured"""
        if not self.MONGODB_URL:
            raise ValueError("MONGODB_URL environment variable is not set")
        
        # Log non-sensitive configuration info
        logger.info(f"Environment: {self.ENVIRONMENT}")
        logger.info(f"API Version: {self.API_V1_STR}")
        logger.info(f"Database Name: {self.MONGODB_DB_NAME}")
        logger.info(f"CORS Origins: {self.get_cors_origins()}")

    def get_cors_origins(self) -> List[str]:
        """Get the list of CORS origins."""
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            try:
                # Split by comma if it's a string
                if isinstance(env_origins, str):
                    additional_origins = [origin.strip() for origin in env_origins.split(",")]
                # Try to evaluate if it's a JSON string
                else:
                    additional_origins = eval(env_origins)
                if isinstance(additional_origins, list):
                    return list(set(self.DEFAULT_CORS_ORIGINS + additional_origins))
            except Exception as e:
                logger.error(f"Error parsing CORS_ORIGINS: {e}")
                return self.DEFAULT_CORS_ORIGINS
        return self.DEFAULT_CORS_ORIGINS

# Initialize settings
settings = Settings()

# Validate settings on import
try:
    settings.validate_settings()
except Exception as e:
    logger.error(f"Configuration error: {str(e)}")
    raise