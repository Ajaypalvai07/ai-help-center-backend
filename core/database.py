import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def init_db():
    """Initialize database connection"""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info(f"Connecting to MongoDB (attempt {retry_count + 1}/{max_retries})...")
            
            # Initialize the MongoDB client with proper settings
            db.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True,
                w='majority'
            )
            
            # Test the connection
            await db.client.admin.command('ping')
            
            # Initialize the database
            db.db = db.client[settings.MONGODB_DB_NAME]
            
            # Verify we can access the database
            await db.db.command('ping')
            
            logger.info("✅ Connected to MongoDB successfully")
            return
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            retry_count += 1
            if retry_count == max_retries:
                logger.error(f"❌ Failed to connect to MongoDB after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(f"Connection attempt {retry_count} failed, retrying...")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to MongoDB: {str(e)}")
            if db.client:
                await close_db()
            raise

async def close_db():
    """Close database connection"""
    try:
        if db.client:
            db.client.close()
            db.client = None
            db.db = None
            logger.info("✅ MongoDB connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing MongoDB connection: {str(e)}")

def get_db():
    """Get database instance"""
    if not db.client or not db.db:
        raise Exception("Database not initialized. Call init_db() first.")
    return db.db 