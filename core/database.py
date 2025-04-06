import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from core.config import settings
import asyncio
from typing import Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    initialized: bool = False

    @classmethod
    async def initialize(cls) -> None:
        """Initialize database connection"""
        if cls.initialized:
            return

        try:
            # Initialize the MongoDB client
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            
            # Test the connection
            await cls.client.admin.command('ping')
            
            # Set the database
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            cls.initialized = True
            
            # Create indexes
            await cls._create_indexes()
            
            logging.info("✅ Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            if cls.client:
                await cls.close()
            raise RuntimeError(f"Database initialization failed: {str(e)}")

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create necessary indexes."""
        try:
            # Create unique index on email for users collection
            await cls.db["users"].create_index("email", unique=True)
            
            # Create indexes for other collections as needed
            await cls.db["messages"].create_index("userId")
            await cls.db["messages"].create_index("timestamp")
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not cls.initialized or cls.db is None:
            raise RuntimeError("Database is not initialized")
        return cls.db

    @classmethod
    async def close(cls) -> None:
        """Close database connection"""
        if cls.client:
            await cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logging.info("Closed MongoDB connection")

# Create a singleton instance
db = Database()

# Initialize and close functions
async def init_db():
    await Database.initialize()

async def close_db():
    await Database.close()

def get_db():
    """Get database instance (sync version)"""
    return db.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance (async version)"""
    if not db.initialized:
        await db.initialize()
    return db.get_db()

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db() 