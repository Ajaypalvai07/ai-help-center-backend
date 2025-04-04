from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

async def get_database():
    """Return database instance"""
    return Database.db

async def init_db():
    """Initialize database connection"""
    try:
        # MongoDB Connection
        Database.client = AsyncIOMotorClient(settings.MONGODB_URL)
        Database.db = Database.client[settings.MONGODB_DB_NAME]
        
        # Test connection
        await Database.client.admin.command('ping')
        print("✅ MongoDB Connected")
        
        # Initialize collections
        collections = await Database.db.list_collection_names()
        
        if 'users' not in collections:
            await Database.db.create_collection('users')
            await Database.db.users.create_index([("email", 1)], unique=True)
            print("✅ Users collection initialized")
            
        return Database.db
        
    except Exception as e:
        print(f"❌ Database Error: {str(e)}")
        raise

async def close_db():
    """Close database connection"""
    if Database.client:
        Database.client.close()
        print("✅ MongoDB Disconnected") 