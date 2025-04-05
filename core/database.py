import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from core.config import settings
import asyncio

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None
    initialized = False

    @classmethod
    async def initialize(cls):
        if cls.initialized:
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
                
                # Initialize the database
                cls.db = cls.client[settings.MONGODB_DB_NAME]
                
                # Verify we can access the database
                await cls.db.command('ping')
                
                cls.initialized = True
                logger.info("✅ Connected to MongoDB successfully")
                return
                
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(f"❌ Failed to connect to MongoDB after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Connection attempt {retry_count} failed, retrying...")
                await asyncio.sleep(1)  # Wait before retrying
                
            except Exception as e:
                logger.error(f"❌ Unexpected error connecting to MongoDB: {str(e)}")
                if cls.client:
                    await cls.close()
                raise

    @classmethod
    async def close(cls):
        """Close database connection"""
        try:
            if cls.client:
                cls.client.close()
                cls.client = None
                cls.db = None
                cls.initialized = False
                logger.info("✅ MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing MongoDB connection: {str(e)}")

    @classmethod
    def get_db(cls):
        """Get database instance (sync version)"""
        if not cls.initialized or not cls.client or not cls.db:
            raise Exception("Database not initialized. Call initialize() first.")
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

def get_db_dependency():
    """For FastAPI dependency injection"""
    if not db.initialized:
        raise Exception("Database not initialized. Call initialize() first.")
    return db.get_db() 