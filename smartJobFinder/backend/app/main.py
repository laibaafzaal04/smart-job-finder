from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.database import db
from app.routes.auth import router as auth_router
from app.routes.profile import router as profile_router
from app.routes.jobs import router as jobs_router
from app.routes.applications import router as applications_router
from app.routes.saved_jobs import router as saved_jobs_router
from app.routes import stats
from app.routes.admin import router as admin_router
from app.routes import user_enhancements


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Job Finder API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware - FIXED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(saved_jobs_router)
app.include_router(stats.router)
app.include_router(admin_router)
app.include_router(user_enhancements.router)

@app.on_event("startup")
async def startup_db_client():
    await db.connect_to_database()
    logger.info("✅ Database connected")

@app.on_event("shutdown")
async def shutdown_db_client():
    await db.close_database_connection()
    logger.info("✅ Database connection closed")

@app.get("/")
async def root():
    return {"message": "Smart Job Finder API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

@app.get("/api/test")
async def test_endpoint():
    return {"message": "CORS test successful"}