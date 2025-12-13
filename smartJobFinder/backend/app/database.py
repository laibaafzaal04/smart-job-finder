from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    async def connect_to_database(self):
        """Connect to MongoDB and initialize the database with indexes."""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.DATABASE_NAME]
            logger.info("✅ Connected to MongoDB")

            # ==========================================
            # CREATE ALL INDEXES FOR PERFORMANCE
            # ==========================================
            
            # 1. USERS COLLECTION
            await self.db.users.create_index("email", unique=True)
            logger.info("✅ Created index: users.email")
            
            # 2. JOBS COLLECTION - Multiple indexes for complex queries
            await self.db.jobs.create_index([("status", 1), ("posted_date", -1)])
            await self.db.jobs.create_index([("skills", 1), ("status", 1)])
            await self.db.jobs.create_index([("location", 1), ("type", 1)])
            await self.db.jobs.create_index("posted_by")
            
            # Full-text search index for jobs
            await self.db.jobs.create_index([
                ("title", "text"),
                ("description", "text"),
                ("company", "text")
            ], name="job_text_search")
            logger.info("✅ Created indexes: jobs collection (5 indexes)")
            
            # 3. APPLICATIONS COLLECTION
            await self.db.applications.create_index([("user_id", 1), ("applied_at", -1)])
            await self.db.applications.create_index([("job_id", 1), ("status", 1)])
            await self.db.applications.create_index([("user_id", 1), ("job_id", 1)], unique=True)
            logger.info("✅ Created indexes: applications collection (3 indexes)")
            
            # 4. SAVED JOBS COLLECTION
            await self.db.saved_jobs.create_index([("user_id", 1), ("saved_at", -1)])
            await self.db.saved_jobs.create_index([("user_id", 1), ("job_id", 1)], unique=True)
            logger.info("✅ Created indexes: saved_jobs collection (2 indexes)")
            
            # 5. PROFILES COLLECTION
            await self.db.profiles.create_index("user_id", unique=True)
            logger.info("✅ Created indexes: profiles collection")
            
            logger.info("✅ All indexes created successfully!")

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    async def close_database_connection(self):
        """Close the MongoDB connection."""
        if self.client is not None:
            self.client.close()
            logger.info("✅ Closed MongoDB connection")

    def get_collection(self, collection_name: str):
        """Return a MongoDB collection safely."""
        if self.db is None:
            raise RuntimeError(
                "Database not connected. Make sure 'connect_to_database()' was called."
            )
        return self.db[collection_name]


# ---------------------- Single global DB instance ----------------------
db = Database()


# ---------------------- Helper function for routes ----------------------
def get_collection(collection_name: str):
    """Helper function to get a collection from the database."""
    return db.get_collection(collection_name)


# ---------------------- Collection names ----------------------
USERS_COLLECTION = "users"
PROFILES_COLLECTION = "profiles"
JOBS_COLLECTION = "jobs"
APPLICATIONS_COLLECTION = "applications"
SAVED_JOBS_COLLECTION = "saved_jobs"