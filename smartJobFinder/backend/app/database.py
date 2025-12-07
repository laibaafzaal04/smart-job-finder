from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None # type: ignore
    db = None
    
    async def connect_to_database(self):
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.DATABASE_NAME]
            logger.info("✅ Connected to MongoDB")
            
            # Create indexes
            await self.db.users.create_index("email", unique=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def close_database_connection(self):
        if self.client:
            self.client.close()
            logger.info("✅ Closed MongoDB connection")

db = Database()

def get_collection(collection_name: str):
    return db.db[collection_name]

# Collection names
USERS_COLLECTION = "users"
PROFILES_COLLECTION = "profiles"
JOBS_COLLECTION = "jobs"
APPLICATIONS_COLLECTION = "applications"
SAVED_JOBS_COLLECTION = "saved_jobs"