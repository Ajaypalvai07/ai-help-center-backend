import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseSettings, Field, validator, SecretStr, Json
from dotenv import load_dotenv
import json
import logging
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Assistant API"
    
    # Environment Settings
    ENVIRONMENT: str = Field(env='ENVIRONMENT', default='development')
    DEBUG: bool = Field(default=True)
    
    # MongoDB Settings
    MONGODB_URL: str = Field(env='MONGODB_URL', default='mongodb://localhost:27017')
    MONGODB_DB_NAME: str = Field(env='MONGODB_DB_NAME', default='fastapi_db')
    MONGODB_OPTIONS: Dict[str, Any] = Field(
        default_factory=lambda: {
            "maxPoolSize": 100,
            "minPoolSize": 10,
            "maxIdleTimeMS": 30000,
            "connectTimeoutMS": 20000,
            "serverSelectionTimeoutMS": 20000,
            "retryWrites": True,
            "w": "majority"
        }
    )
    
    # JWT Settings
    SECRET_KEY: str = Field(env='SECRET_KEY', default='your-secret-key-here')
    ALGORITHM: str = Field(env='ALGORITHM', default='HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(env='ACCESS_TOKEN_EXPIRE_MINUTES', default=30)
    
    # Security Settings
    ENCRYPTION_KEY: SecretStr = Field(env='ENCRYPTION_KEY', default='your-encryption-key-here')
    CORS_ORIGINS: List[str] = Field(default=["*"])
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_PERIOD: int = Field(default=60)
    
    # Hugging Face Settings
    USE_HUGGINGFACE: bool = Field(env='USE_HUGGINGFACE', default=False)
    HUGGINGFACE_API_KEY: SecretStr = Field(env='HUGGINGFACE_API_KEY', default='')
    HUGGINGFACE_MODEL: str = Field(env='HUGGINGFACE_MODEL', default='google/flan-t5-base')

    class Config:
        case_sensitive = True
        env_file = '.env'
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None
        }
        
    @validator('MONGODB_OPTIONS', pre=True)
    def parse_mongodb_options(cls, v: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v
        
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v

    def get_mongodb_url(self) -> str:
        """Get the MongoDB connection URL"""
        return self.MONGODB_URL

    def get_secret_key(self) -> str:
        """Get the secret key for JWT"""
        return self.SECRET_KEY

    def get_encryption_key(self) -> str:
        """Get the encryption key"""
        return self.ENCRYPTION_KEY.get_secret_value()

    def get_huggingface_api_key(self) -> str:
        """Get the Hugging Face API key"""
        return self.HUGGINGFACE_API_KEY.get_secret_value()

    def validate_settings(self) -> None:
        """Validate critical settings"""
        if self.ENVIRONMENT == 'production':
            assert self.SECRET_KEY != 'your-secret-key-here', "Production environment requires a secure SECRET_KEY"
            assert self.ENCRYPTION_KEY.get_secret_value() != 'your-encryption-key-here', "Production environment requires a secure ENCRYPTION_KEY"
            assert "*" not in self.CORS_ORIGINS, "Production environment should not allow all origins"

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Override dict method to handle SecretStr fields"""
        d = super().dict(*args, **kwargs)
        # Convert SecretStr to string representation
        for key, value in d.items():
            if isinstance(value, SecretStr):
                d[key] = value.get_secret_value()
        return d

@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    settings = Settings()
    if os.getenv('VALIDATE_SETTINGS', '').lower() == 'true':
        settings.validate_settings()
    return settings

# Initialize settings
try:
    settings = get_settings()
except Exception as e:
    logger.error(f"Configuration error: {str(e)}")
    raise