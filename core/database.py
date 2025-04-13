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
from .config import get_settings, Settings

settings = get_settings()
logger = logging.getLogger(__name__)

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB BSON types"""
    def default(self, obj):
        if isinstance(obj, (datetime, ObjectId)):
            return str(obj)
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
        """Initialize database connection and setup"""
        if cls.initialized:
            return

        settings: Settings = get_settings()
        try:
            logger.info("Initializing database connection...")
            cls.client = AsyncIOMotorClient(
                settings.get_mongodb_url(),
                **settings.MONGODB_OPTIONS
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
            
            # Clean up null usernames before creating indexes
            await cls._cleanup_null_usernames()
            
            # Create indexes after cleanup
            await cls._create_indexes()
            
            cls.initialized = True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            if cls.client:
                cls.client.close()
            cls.client = None
            cls.db = None
            raise

    @classmethod
    async def _cleanup_null_usernames(cls) -> None:
        """Clean up users with null usernames"""
        try:
            # Find users with null usernames
            async for user in cls.db.users.find({"username": None}):
                # Generate a username based on email or a default pattern
                email_prefix = user.get('email', '').split('@')[0] if user.get('email') else f'user_{str(user["_id"])}'
                new_username = email_prefix
                
                # Ensure username uniqueness
                counter = 1
                while await cls.db.users.find_one({"username": new_username}):
                    new_username = f"{email_prefix}_{counter}"
                    counter += 1
                
                # Update the user with the new username
                await cls.db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"username": new_username}}
                )
                logger.info(f"Updated null username for user {user['_id']} to {new_username}")
                
        except Exception as e:
            logger.error(f"Error cleaning up null usernames: {str(e)}")
            raise

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create database indexes"""
        try:
            # Drop existing indexes to recreate them
            try:
                await cls.db.users.drop_indexes()
                await cls.db.messages.drop_indexes()
                await cls.db.categories.drop_indexes()
                logger.info("Dropped existing indexes")
            except Exception as e:
                logger.warning(f"Error dropping indexes (this is okay for first run): {str(e)}")

            # Create indexes
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("username", unique=True)
            await cls.db.messages.create_index([("user_id", 1), ("created_at", -1)])
            await cls.db.categories.create_index("name", unique=True)
            logger.info("Created database indexes successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not cls.initialized or not cls.db:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls.db

    @classmethod
    async def close(cls) -> None:
        """Close database connection"""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logger.info("Closed database connection")

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

async def init_db() -> None:
    """Initialize database connection"""
    await Database.initialize()

async def close_db() -> None:
    """Close database connection"""
    await Database.close()

def get_db() -> AsyncIOMotorDatabase:
    """Get database instance synchronously"""
    return Database.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance asynchronously"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

db = Database()
