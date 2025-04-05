import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from core.config import settings
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    initialized: bool = False

    @classmethod
    async def initialize(cls) -> None:
        """Initialize database connection with retry mechanism."""
        if cls.initialized and cls.client is not None and cls.db is not None:
            return

        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                logger.info(f"Connecting to MongoDB (attempt {retry_count + 1}/{max_retries})...")
                
                # Initialize the MongoDB client with proper settings for serverless
                cls.client = AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=20000,
                    maxPoolSize=1,
                    minPoolSize=0,
                    maxIdleTimeMS=5000,
                    waitQueueTimeoutMS=5000,
                    retryWrites=True,
                    w='majority'
                )
                
                # Test the connection
                await cls.client.admin.command('ping')
                
                # Initialize database
                cls.db = cls.client[settings.MONGODB_DB_NAME]
                cls.initialized = True
                
                logger.info("✅ Connected to MongoDB successfully")
                return
                
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(f"❌ Failed to connect to MongoDB after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Connection attempt {retry_count} failed, retrying...")
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Unexpected error connecting to MongoDB: {str(e)}")
                raise

    @classmethod
    async def close(cls) -> None:
        """Close database connection."""
        if cls.client is not None:
            try:
                cls.client.close()
                cls.client = None
                cls.db = None
                cls.initialized = False
                logger.info("✅ Database connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing database connection: {str(e)}")
                raise

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.db is None:
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

async def get_database():
    """Get database instance (async version)"""
    if not db.initialized:
        await db.initialize()
    return db.get_db()

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for getting database instance."""
    if Database.db is None:
        await Database.initialize()
    return Database.get_db() 