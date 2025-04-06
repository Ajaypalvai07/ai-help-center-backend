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

        max_retries = 5
        retry_delay = 2  # seconds
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{max_retries})")
                
                # Close existing connection if any
                if cls.client:
                    await cls.close()
                
                # Initialize the MongoDB client with explicit options
                cls.client = AsyncIOMotorClient(
                    settings.MONGODB_URL,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    maxPoolSize=10,
                    retryWrites=True,
                    w='majority'
                )
                
                # Test the connection
                await cls.client.admin.command('ping')
                logger.info("MongoDB ping successful")
                
                # Set the database
                cls.db = cls.client[settings.MONGODB_DB_NAME]
                
                # Verify database access
                await cls.db.command('ping')
                logger.info("Database access verified")
                
                # Create indexes
                await cls._create_indexes()
                
                cls.initialized = True
                logger.info("✅ Successfully connected to MongoDB")
                return
                
            except (ServerSelectionTimeoutError, ConnectionFailure) as e:
                last_error = str(e)
                logger.error(f"Failed to connect to MongoDB (attempt {attempt + 1}): {last_error}")
                if cls.client:
                    await cls.close()
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ Unexpected error during database initialization: {last_error}")
                if cls.client:
                    await cls.close()
                raise RuntimeError(f"Database initialization failed: {last_error}")

        # If we get here, all retries failed
        raise RuntimeError(f"Failed to initialize database after {max_retries} attempts. Last error: {last_error}")

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create necessary indexes"""
        if not cls.db:
            raise RuntimeError("Database not initialized")
            
        try:
            # Create unique index on email for users collection
            await cls.db["users"].create_index("email", unique=True)
            
            # Create indexes for other collections
            await cls.db["messages"].create_index("userId")
            await cls.db["messages"].create_index("timestamp")
            
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
        if cls.client:
            await cls.client.close()
            cls.client = None
            cls.db = None
            cls.initialized = False
            logger.info("✅ Closed MongoDB connection")

async def get_db_dependency() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access"""
    try:
        if not Database.initialized or Database.db is None:
            await Database.initialize()
        return Database.get_db()
    except Exception as e:
        logger.error(f"Failed to get database connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

# Initialize database connection
async def init_db():
    await Database.initialize()

# Close database connection
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

# Create a singleton instance
db = Database() 