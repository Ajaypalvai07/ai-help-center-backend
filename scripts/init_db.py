import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def init_db():
    """Initialize the database with required collections and indexes."""
    settings = get_settings()
    client = None
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]
        logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")

        # Create collections
        collections = ["users", "messages", "categories"]
        for collection in collections:
            if collection not in await db.list_collection_names():
                await db.create_collection(collection)
                logger.info(f"Created collection: {collection}")

        # Create indexes
        # Users collection indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)
        logger.info("Created indexes for users collection")

        # Messages collection indexes
        await db.messages.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("Created indexes for messages collection")

        # Categories collection indexes
        await db.categories.create_index("name", unique=True)
        logger.info("Created indexes for categories collection")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if client:
            client.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(init_db()) 