import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # MongoDB - Updated for production
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "smartjobfinder")
    
    # JWT
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    # Admin
    ADMIN_REGISTRATION_CODE = os.getenv("ADMIN_REGISTRATION_CODE", "ADMIN2024")
    
    # Email Settings
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@smartjobfinder.com")
    EMAIL_SERVER = os.getenv("EMAIL_SERVER", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    
    # Frontend URL - UPDATED for correct path structure
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500/smartJobFinder/frontend")
    
    # File Upload (disable for Render free tier - ephemeral filesystem)
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 5 * 1024 * 1024))  # 5MB
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
    
    # CORS - MUST include your frontend domain
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5500").split(",")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Groq API
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

settings = Settings()