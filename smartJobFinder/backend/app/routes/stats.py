from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
from bson import ObjectId

from app.database import get_collection, USERS_COLLECTION, APPLICATIONS_COLLECTION, SAVED_JOBS_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stats", tags=["stats"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.get("/user-dashboard")
async def get_user_dashboard_stats(token: str = Depends(oauth2_scheme)):
    """Get user dashboard statistics"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = str(user["_id"])
    
    try:
        # Count applications
        applications_count = await applications_collection.count_documents({
            "user_id": user_id
        })
        
        # Count saved jobs
        saved_jobs_count = await saved_jobs_collection.count_documents({
            "user_id": user_id
        })
        
        # Get applications with interview status
        interview_applications = await applications_collection.count_documents({
            "user_id": user_id,
            "status": {"$in": ["interview", "Interview Scheduled", "shortlisted"]}
        })
        
        # Get user profile views (for now, we'll use a fixed number or calculate based on profile completeness)
        profile_completion = user.get("profile_completed", False)
        profile_views = 0
        
        # Calculate profile views based on profile completeness
        if profile_completion:
            # Base views plus some random factor
            profile_views = 5 + applications_count
        
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        applications_count = 0
        saved_jobs_count = 0
        interview_applications = 0
        profile_views = 0
    
    return {
        "user_id": user_id,
        "applications_count": applications_count,
        "saved_jobs_count": saved_jobs_count,
        "interviews_count": interview_applications,
        "profile_views": profile_views,
        "profile_completed": user.get("profile_completed", False)
    }  