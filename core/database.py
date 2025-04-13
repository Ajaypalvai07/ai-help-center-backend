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
    initialized: bool = False  # Add this line
    json_encoder = JSONEncoder()

    @classmethod
    async def initialize(cls) -> None:
        """Initialize database connection"""
        if cls.client is not None:
            return

        try:
            cls.client = AsyncIOMotorClient(
                settings.get_mongodb_url(),
                **settings.MONGODB_OPTIONS
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB at {settings.get_mongodb_url()}")
            logger.info(f"Using database: {settings.MONGODB_DB_NAME}")

            await cls._create_indexes()  # Optional but good to call here
            cls.initialized = True  # Set initialized to True

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create database indexes"""
        try:
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("role")
            await cls.db.messages.create_index([("user_id", 1), ("created_at", -1)])
            await cls.db.messages.create_index("category")
            await cls.db.feedback.create_index([("message_id", 1), ("user_id", 1)])
            await cls.db.feedback.create_index("created_at")
            logger.info("✅ Database indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {str(e)}")
            raise

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls.db is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls.db

    @classmethod
    async def close(cls) -> None:
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logger.info("Closed MongoDB connection")


async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

# Initialize database on startup
async def init_db() -> None:
    await Database.initialize()

# Close database on shutdown
async def close_db() -> None:
    await Database.close()

def get_db() -> AsyncIOMotorDatabase:
    """Synchronous database getter"""
    return Database.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Asynchronous database getter"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

db = Database()
