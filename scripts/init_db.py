from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime
from ..core.config import settings
import logging

async def init_database():
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]
        
        # Create collections if they don't exist
        collections = await db.list_collection_names()
        
        if "users" not in collections:
            await db.create_collection("users")
            # Create default admin user
            await db.users.insert_one({
                "email": "admin@example.com",
                "password": "admin123",  # Change this in production
                "role": "admin",
                "is_active": True,
                "created_at": datetime.utcnow()
            })
        
        if "messages" not in collections:
            await db.create_collection("messages")
        
        if "system_logs" not in collections:
            await db.create_collection("system_logs", capped=True, size=5242880)
        
        # Create indexes
        await db.users.create_index("email", unique=True)
        await db.users.create_index("role")
        
        await db.messages.create_index("user_id")
        await db.messages.create_index("created_at")
        await db.messages.create_index("category")
        await db.messages.create_index("status")
        await db.messages.create_index([("created_at", -1), ("category", 1)])
        
        await db.system_logs.create_index("timestamp")
        await db.system_logs.create_index([("timestamp", -1), ("level", 1)])
        
        # Log success
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_database()) 