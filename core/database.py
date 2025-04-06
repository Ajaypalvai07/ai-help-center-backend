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

            # Test connection
            await cls.client.admin.command('ping')
            logger.info("MongoDB connection successful")

            # Initialize database
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            await cls.db.command('ping')
            logger.info(f"Connected to database: {settings.MONGODB_DB_NAME}")

            # Create indexes
            await cls._create_indexes()

            cls.initialized = True
            logger.info("✅ Database initialization complete")

        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ Failed to connect to MongoDB server: {str(e)}")
            if cls.client is not None:
                await cls.close()
            raise RuntimeError(f"Could not connect to MongoDB server: {str(e)}")
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            if cls.client is not None:
                await cls.close()
            raise RuntimeError(f"MongoDB connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            if cls.client is not None:
                await cls.close()
            raise RuntimeError(f"Failed to initialize database: {str(e)}")

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create necessary indexes"""
        if cls.db is None:
            raise RuntimeError("Database not initialized")
            
        try:
            # Create unique index on email for users collection
            await cls.db["users"].create_index("email", unique=True)
            
            # Create indexes for other collections
            await cls.db["messages"].create_index([("userId", 1), ("timestamp", -1)])
            await cls.db["feedback"].create_index("userId")
            
            logger.info("✅ Database indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {str(e)}")
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
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logger.info("✅ Closed MongoDB connection")

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access"""
    if not Database.initialized or Database.db is None:
        await Database.initialize()
    return Database.get_db()

# Initialize database connection
async def init_db():
    """Initialize database connection"""
    await Database.initialize()

# Close database connection
async def close_db():
    """Close database connection"""
    await Database.close()

def get_db():
    """Get database instance (sync version)"""
    return db.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance (async version)"""
    if not db.initialized:
        await db.initialize()
    return db.get_db()

# Create a singleton instance
db = Database() 