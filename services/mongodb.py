from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List, Dict, Any, Tuple, TypeVar, cast, Union
from datetime import datetime
import logging
from core.config import settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Dict[str, Any])

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        # Create indexes
        await self.create_indexes()
        
    async def close(self):
        if self.client:
            self.client.close()
            
    async def create_indexes(self):
        # Create unique index on email for users collection
        await self.db.users.create_index("email", unique=True)

mongodb = MongoDB()

async def get_mongodb():
    return mongodb

class MongoDBService:
    _instance = None
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Connect to MongoDB database"""
        if not self.client:
            try:
                settings = get_settings()
                self.client = AsyncIOMotorClient(settings.MONGODB_URL)
                self.db = self.client[settings.MONGODB_DB_NAME]
                # Test connection
                await self.db.command('ping')
                logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
            except Exception as e:
                logger.error(f"MongoDB connection error: {str(e)}")
                raise

    async def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("Closed MongoDB connection")

    def _check_connection(self):
        """Check if database connection is initialized"""
        if not self.db:
            raise RuntimeError("Database connection not initialized")

    async def create_indexes(self) -> None:
        """Create database indexes"""
        try:
            self._check_connection()
            # Users collection indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.users.create_index("username", unique=True)
            # Messages collection indexes
            await self.db.messages.create_index([("user_id", 1), ("created_at", -1)])
            # Categories collection indexes
            await self.db.categories.create_index("name", unique=True)
            logger.info("Created database indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {str(e)}")
            raise

    async def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document"""
        try:
            self._check_connection()
            return await self.db[collection].find_one(query)
        except Exception as e:
            logger.error(f"Error in find_one: {str(e)}")
            raise

    async def find(self, collection: str, query: Dict[str, Any], sort: Optional[List[Tuple[str, int]]] = None) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        try:
            self._check_connection()
            cursor = self.db[collection].find(query)
            if sort:
                cursor = cursor.sort(sort)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error in find: {str(e)}")
            raise

    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert a single document"""
        try:
            self._check_connection()
            result = await self.db[collection].insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error in insert_one: {str(e)}")
            raise

    async def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        """Update a single document"""
        try:
            self._check_connection()
            result = await self.db[collection].update_one(query, {"$set": update})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error in update_one: {str(e)}")
            raise

    # Generic CRUD operations
    async def find_many(
        self,
        collection: str,
        query: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        try:
            self._check_connection()
            cursor = self.db[collection].find(query).skip(skip).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            results = await cursor.to_list(length=limit)
            for result in results:
                result["id"] = str(result.pop("_id"))
            return results
        except Exception as e:
            logger.error(f"Error finding documents in {collection}: {str(e)}")
            raise

    async def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        """Delete a single document"""
        try:
            self._check_connection()
            result = await self.db[collection].delete_one(query)
            return bool(result.deleted_count > 0)
        except Exception as e:
            logger.error(f"Error deleting document from {collection}: {str(e)}")
            raise

    # User operations
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            self._check_connection()
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        except Exception:
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        if self.db is None:
            raise ValueError("Database not initialized")
        user = await self.db.users.find_one({"email": email})
        if user:
            user["id"] = str(user.pop("_id"))
        return user

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.db is None:
            raise ValueError("Database not initialized")
        result = await self.db.users.insert_one(user_data)
        return await self.get_user(str(result.inserted_id))

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.db is None:
            raise ValueError("Database not initialized")
        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        if result.modified_count:
            return await self.get_user(user_id)
        return None

    async def delete_user(self, user_id: str) -> bool:
        if self.db is None:
            raise ValueError("Database not initialized")
        result = await self.db.users.delete_one({"_id": ObjectId(user_id)})
        return bool(result.deleted_count > 0)

    # Message operations
    async def create_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.db is None:
            raise ValueError("Database not initialized")
        message_data["created_at"] = datetime.utcnow()
        result = await self.db.messages.insert_one(message_data)
        created = await self.db.messages.find_one({"_id": result.inserted_id})
        if not created:
            raise ValueError("Failed to retrieve created message")
        created["id"] = str(created.pop("_id"))
        return created

    async def get_user_messages(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if self.db is None:
            raise ValueError("Database not initialized")
        cursor = self.db.messages.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        messages = await cursor.to_list(length=limit)
        for msg in messages:
            msg["id"] = str(msg.pop("_id"))
        return messages

    # Feedback operations
    async def create_feedback(self, feedback_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.db is None:
            raise ValueError("Database not initialized")
        result = await self.db.feedback.insert_one(feedback_data)
        return await self.db.feedback.find_one({"_id": result.inserted_id})

    # Stats operations
    async def get_stats(self) -> Dict[str, Any]:
        if self.db is None:
            raise ValueError("Database not initialized")
        users_count = await self.db.users.count_documents({})
        messages_count = await self.db.messages.count_documents({})
        resolved_count = await self.db.messages.count_documents({"status": "resolved"})
        
        return {
            "total_users": users_count,
            "total_messages": messages_count,
            "resolved_issues": resolved_count,
            "resolution_rate": (resolved_count / messages_count * 100) if messages_count > 0 else 0
        }

# Create a singleton instance
mongodb_service = MongoDBService() 