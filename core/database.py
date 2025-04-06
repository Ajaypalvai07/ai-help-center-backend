import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, OperationFailure
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
        # Check if already initialized with valid connection
        if cls.initialized and cls.db is not None and cls.client is not None:
            try:
                await cls.db.command('ping')
                logger.info("Using existing database connection")
                return
            except Exception as e:
                logger.warning(f"Existing connection is stale: {str(e)}, reinitializing...")
                await cls.close()

        if not settings.MONGODB_URL:
            raise ValueError("MONGODB_URL environment variable is not set")

        try:
            logger.info("Initializing MongoDB connection...")
            
            # Create MongoDB client with explicit options
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=10,
                retryWrites=True,
                retryReads=True,
                waitQueueTimeoutMS=5000
            )

            # Test the connection with timeout
            try:
                await asyncio.wait_for(
                    cls.client.admin.command('ping'),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.error("Database connection timed out")
                await cls.close()
                raise ConnectionFailure("Database connection timed out")
            
            # Get database instance
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Verify database access
            await cls.db.command('ping')
            
            # Set initialized flag before creating indexes
            cls.initialized = True
            
            # Create indexes
            await cls._create_indexes()
            
            logger.info("✅ MongoDB connection initialized successfully")
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            await cls.close()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection failed: {str(e)}"
            )
        except OperationFailure as e:
            logger.error(f"MongoDB operation failed: {str(e)}")
            await cls.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database operation failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {str(e)}", exc_info=True)
            await cls.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database initialization failed: {str(e)}"
            )

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create necessary database indexes"""
        if cls.db is None:
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
        try:
            if cls.client is not None:
                cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
            cls.client = None
            cls.db = None
            cls.initialized = False

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for getting database instance"""
    if not Database.initialized or Database.db is None:
        try:
            await Database.initialize()
        except Exception as e:
            logger.error(f"Error in get_db_dependency: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
    return Database.get_db()

async def init_db():
    """Initialize database connection"""
    await Database.initialize()

async def close_db():
    """Close database connection"""
    await Database.close()

def get_db():
    """Get database instance"""
    if not Database.initialized or Database.db is None:
        raise RuntimeError("Database is not initialized")
    return Database.get_db()

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance with initialization check"""
    if not Database.initialized or Database.db is None:
        await Database.initialize()
    return Database.get_db()

# Create a singleton instance
db = Database() 