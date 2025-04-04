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
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://*.netlify.app",
        "https://*.railway.app",
        "https://your-domain.com"  # Add your custom domain if you have one
    ]

    def get_cors_origins(self) -> List[str]:
        """Get the list of CORS origins."""
        # Get additional origins from environment variable if set
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            try:
                additional_origins = eval(env_origins)
                if isinstance(additional_origins, list):
                    return self.CORS_ORIGINS + additional_origins
            except:
                pass
        return self.CORS_ORIGINS

# Initialize settings
settings = Settings()