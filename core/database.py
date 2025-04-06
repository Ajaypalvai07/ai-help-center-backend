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
        """Initialize database connection with retries"""
        if cls.initialized and cls.db is not None:
            return

        if not settings.MONGODB_URL:
            raise ValueError("MONGODB_URL environment variable is not set")

        try:
            # Close any existing connection
            if cls.client is not None:
                await cls.close()

            logger.info("Initializing MongoDB connection...")
            
            # Create MongoDB client with explicit options
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True
            )

            # Test the connection
            await cls.client.admin.command('ping')
            
            # Get database instance
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            cls.initialized = True
            
            # Create indexes
            await cls._create_indexes()
            
            logger.info("✅ MongoDB connection initialized successfully")
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            if cls.client:
                await cls.close()
            cls.initialized = False
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {str(e)}")
            if cls.client:
                await cls.close()
            cls.initialized = False
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database initialization failed"
            )

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create necessary database indexes"""
        if not cls.db:
            raise RuntimeError("Database not initialized")
        
        try:
            # Create unique index on email for users collection
            await cls.db.users.create_index("email", unique=True)
            
            # Create indexes for messages collection
            await cls.db.messages.create_index([("user_id", 1), ("timestamp", -1)])
            await cls.db.messages.create_index("category")
            
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
            try:
                cls.client.close()
                cls.client = None
                cls.db = None
                cls.initialized = False
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for getting database instance"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

async def init_db():
    """Initialize database connection"""
    await Database.initialize()

async def close_db():
    """Close database connection"""
    await Database.close()

def get_db():
    """Get database instance"""
    return Database.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance with initialization check"""
    if not Database.initialized:
        await Database.initialize()
    return Database.get_db()

# Create a singleton instance
db = Database() 