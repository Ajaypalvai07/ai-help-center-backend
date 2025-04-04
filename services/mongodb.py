from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List, Dict, Any, Tuple, TypeVar, cast, Union
from datetime import datetime
import logging
from core.config import settings

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
    def __init__(self):
        self.client: Union[None, AsyncIOMotorClient] = None
        self.db: Union[None, AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB_NAME]
            # Verify connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            # Create indexes
            await self.create_indexes()
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {str(e)}")
            raise

    async def close(self) -> None:
        """Close MongoDB connection"""
        if self.client is not None:
            self.client.close()
            logger.info("MongoDB connection closed")

    async def create_indexes(self) -> None:
        """Create necessary indexes"""
        try:
            if self.db is None:
                raise ValueError("Database not initialized")
                
            # Users collection indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.users.create_index("username", unique=True)
            
            # Messages collection indexes
            await self.db.messages.create_index([("user_id", 1), ("created_at", -1)])
            await self.db.messages.create_index("category")
            
            # Feedback collection indexes
            await self.db.feedback.create_index("message_id")
            await self.db.feedback.create_index("user_id")
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating MongoDB indexes: {str(e)}")
            raise

    # Generic CRUD operations
    async def insert_one(self, collection: str, data: Dict[str, Any]) -> str:
        """Insert a single document"""
        try:
            if self.db is None:
                raise ValueError("Database not initialized")
            result = await self.db[collection].insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error inserting document into {collection}: {str(e)}")
            raise

    async def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document"""
        try:
            if self.db is None:
                raise ValueError("Database not initialized")
            result = await self.db[collection].find_one(query)
            if result:
                result["id"] = str(result.pop("_id"))
            return result
        except Exception as e:
            logger.error(f"Error finding document in {collection}: {str(e)}")
            raise

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
            if self.db is None:
                raise ValueError("Database not initialized")
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

    async def update_one(
        self,
        collection: str,
        query: Dict[str, Any],
        update_data: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """Update a single document"""
        try:
            if self.db is None:
                raise ValueError("Database not initialized")
            result = await self.db[collection].update_one(
                query,
                {"$set": update_data},
                upsert=upsert
            )
            return bool(result.modified_count > 0 or (upsert and result.upserted_id))
        except Exception as e:
            logger.error(f"Error updating document in {collection}: {str(e)}")
            raise

    async def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        """Delete a single document"""
        try:
            if self.db is None:
                raise ValueError("Database not initialized")
            result = await self.db[collection].delete_one(query)
            return bool(result.deleted_count > 0)
        except Exception as e:
            logger.error(f"Error deleting document from {collection}: {str(e)}")
            raise

    # User operations
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            if self.db is None:
                raise ValueError("Database not initialized")
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

# Initialize MongoDB service
mongodb_service = MongoDBService() 