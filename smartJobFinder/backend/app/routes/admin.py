# backend/app/routes/admin.py
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import logging
from bson import ObjectId

from app.database import get_collection, USERS_COLLECTION, JOBS_COLLECTION, APPLICATIONS_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.get("/dashboard-stats")
async def get_admin_dashboard_stats(token: str = Depends(oauth2_scheme)):
    """Get comprehensive dashboard stats for admin"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    admin_email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": admin_email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    admin_id = str(admin_user["_id"])
    
    try:
        # Count total jobs posted by this admin
        total_jobs = await jobs_collection.count_documents({
            "posted_by": admin_id
        })
        
        # Count active jobs
        active_jobs = await jobs_collection.count_documents({
            "posted_by": admin_id,
            "status": "active"
        })
        
        # Get admin's job IDs
        admin_jobs = await jobs_collection.find({"posted_by": admin_id}).to_list(length=100)
        admin_job_ids = [str(job["_id"]) for job in admin_jobs]
        
        # Initialize counts
        pending_applications = 0
        unique_applicants = 0
        
        if admin_job_ids:
            # Count pending applications for admin's jobs
            pending_applications = await applications_collection.count_documents({
                "job_id": {"$in": admin_job_ids},
                "status": "pending"
            })
            
            # Get unique applicants for admin's jobs
            pipeline = [
                {"$match": {"job_id": {"$in": admin_job_ids}}},
                {"$group": {"_id": "$user_id"}},
                {"$count": "unique_count"}
            ]
            
            result = await applications_collection.aggregate(pipeline).to_list(length=1)
            if result and result[0]:
                unique_applicants = result[0].get("unique_count", 0)
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "pending_applications": pending_applications,
            "unique_applicants": unique_applicants,
            "admin_id": admin_id,
            "admin_email": admin_email
        }
        
    except Exception as e:
        logger.error(f"Error calculating admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating statistics"
        )