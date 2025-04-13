import logging
import asyncio
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, OperationFailure
from fastapi import HTTPException, status
from core.config import settings  # Ensure settings.MONGODB_URL is of type SecretStr
from bson import ObjectId, json_util, Decimal128
import json
from datetime import datetime
from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB BSON types"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal128):
            return float(obj.to_decimal())
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        return json.JSONEncoder.default(self, obj)

class Database:
    """Database connection manager"""
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    initialized: bool = False
    json_encoder = JSONEncoder()

    @classmethod
    async def initialize(cls) -> None:
        """Initialize database connection"""
        if cls.initialized:
            return

        try:
            logger.info("Initializing database connection...")
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                **settings.MONGODB_OPTIONS
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await cls.db.command("ping")
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
            
            # Create indexes
            await cls._create_indexes()
            
            cls.initialized = True
            logger.info("Database initialization complete")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            if cls.client:
                cls.client.close()
                cls.client = None
            cls.db = None
            cls.initialized = False
            raise

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create database indexes"""
        try:
            # Users collection indexes
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("username", unique=True)
            await cls.db.users.create_index([("role", 1), ("is_active", 1)])

            # Messages collection indexes
            await cls.db.messages.create_index([("user_id", 1), ("created_at", -1)])
            await cls.db.messages.create_index([("category", 1), ("created_at", -1)])

            # Categories collection indexes
            await cls.db.categories.create_index("name", unique=True)
            await cls.db.categories.create_index("active")

            # Feedback collection indexes
            await cls.db.feedback.create_index([("message_id", 1), ("created_at", -1)])
            await cls.db.feedback.create_index([("user_id", 1), ("created_at", -1)])

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not cls.initialized or not cls.db:
            raise RuntimeError("Database not initialized")
        return cls.db

    @classmethod
    async def close(cls) -> None:
        """Close database connection"""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logger.info("Database connection closed")

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

# Convenience functions
async def init_db() -> None:
    """Initialize database connection"""
    await Database.initialize()

async def close_db() -> None:
    """Close database connection"""
    await Database.close()

def get_db() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return Database.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Async function to get database instance"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

db = Database()
