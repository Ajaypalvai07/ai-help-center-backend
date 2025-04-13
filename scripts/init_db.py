import re
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import get_settings
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def sanitize_username(username: str) -> str:
    """Convert username to valid format."""
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', username)
    # Ensure minimum length
    if len(sanitized) < 3:
        sanitized = sanitized + "_" * (3 - len(sanitized))
    # Truncate if too long
    return sanitized[:50]

async def generate_unique_username(db, base_username: str) -> str:
    """Generate a unique username by adding numbers if needed."""
    username = await sanitize_username(base_username)
    counter = 1
    while await db.users.find_one({"username": username}):
        suffix = f"_{counter}"
        username = f"{base_username[:50-len(suffix)]}{suffix}"
        counter += 1
    return username

async def cleanup_usernames(db) -> None:
    """Clean up invalid usernames in the database."""
    valid_username_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    async for user in db.users.find({"$or": [
        {"username": None},
        {"username": {"$exists": False}},
        {"username": {"$not": valid_username_pattern}}
    ]}):
        old_username = user.get("username", None)
        base_username = old_username or user.get("email", "user").split("@")[0]
        new_username = await generate_unique_username(db, base_username)
        
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"username": new_username}}
        )
        logger.info(f"Updated username: {old_username} -> {new_username}")

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
        collections = ["users", "messages", "categories", "feedback"]
        for collection in collections:
            if collection not in await db.list_collection_names():
                await db.create_collection(collection)
                logger.info(f"Created collection: {collection}")

        # Clean up invalid usernames first
        await cleanup_usernames(db)

        # Drop existing indexes to avoid conflicts
        try:
            await db.users.drop_indexes()
            await db.messages.drop_indexes()
            await db.categories.drop_indexes()
            logger.info("Dropped existing indexes")
        except Exception as e:
            logger.warning(f"Error dropping indexes: {e}")

        # Create indexes
        # Users collection indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("username", unique=True)
        await db.users.create_index([("role", 1), ("is_active", 1)])
        logger.info("Created indexes for users collection")

        # Messages collection indexes
        await db.messages.create_index([("user_id", 1), ("created_at", -1)])
        await db.messages.create_index([("category", 1), ("created_at", -1)])
        logger.info("Created indexes for messages collection")

        # Categories collection indexes
        await db.categories.create_index("name", unique=True)
        await db.categories.create_index("active")
        logger.info("Created indexes for categories collection")

        # Feedback collection indexes
        await db.feedback.create_index([("message_id", 1), ("created_at", -1)])
        await db.feedback.create_index([("user_id", 1), ("created_at", -1)])
        logger.info("Created indexes for feedback collection")

        # Create default admin user if not exists
        admin_user = await db.users.find_one({"email": "admin@example.com"})
        if not admin_user:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin_doc = {
                "email": "admin@example.com",
                "username": "admin",
                "full_name": "System Admin",
                "hashed_password": pwd_context.hash("admin123"),
                "role": "admin",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "preferences": {}
            }
            await db.users.insert_one(admin_doc)
            logger.info("Created default admin user")

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