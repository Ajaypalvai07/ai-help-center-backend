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
        """Initialize database connection."""
        if cls.initialized:
            return

        try:
            logger.info("Connecting to MongoDB...")
            
            # Create client with proper settings for Atlas
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True,
                w='majority',
                journal=True
            )
            
            # Get database instance
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test the connection
            try:
                await cls.db.command('ping')
                logger.info("Successfully connected to MongoDB Atlas")
            except Exception as e:
                logger.error(f"Failed to ping database: {str(e)}")
                raise

            cls.initialized = True
            
            # Create indexes
            await cls._create_indexes()
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {str(e)}")
            if cls.client:
                cls.client.close()
            cls.initialized = False
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not connect to database server"
            )
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failure: {str(e)}")
            if cls.client:
                cls.client.close()
            cls.initialized = False
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to establish database connection"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            if cls.client:
                cls.client.close()
            cls.initialized = False
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database initialization failed"
            )

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
    async def close(cls) -> None:
        """Close database connection."""
        if cls.client:
            try:
                cls.client.close()
                cls.client = None
                cls.db = None
                cls.initialized = False
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
                raise

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if not cls.initialized or not cls.db:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls.db

# Create a singleton instance
db = Database()

# Initialize and close functions
async def init_db():
    """Initialize the database connection"""
    await db.initialize()

async def close_db():
    """Close the database connection"""
    await db.close()

def get_db():
    """Get database instance (sync version)"""
    return db.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance (async version)"""
    if not db.initialized:
        await db.initialize()
    return db.get_db()

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    try:
        if not Database.initialized:
            await Database.initialize()
        return Database.get_db()
    except Exception as e:
        logger.error(f"Error getting database connection: {str(e)}")
        raise 