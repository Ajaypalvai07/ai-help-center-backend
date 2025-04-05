from typing import List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Assistant API"

    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "ai_assistance")

    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # CORS settings
    DEFAULT_CORS_ORIGINS: List[str] = [
        "https://ai-help-center-frontend-vkp9.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173"
    ]

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
                print(f"Error parsing CORS_ORIGINS: {e}")
                return self.DEFAULT_CORS_ORIGINS
        return self.DEFAULT_CORS_ORIGINS

# Initialize settings
settings = Settings()