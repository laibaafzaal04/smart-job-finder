# backend/app/routes/user_enhancements.py
"""
Enhanced routes for user-side functionality - UPDATED FOR FULL FRONTEND INTEGRATION
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import logging
from typing import List, Optional
from bson import ObjectId

from app.database import get_collection, JOBS_COLLECTION, SAVED_JOBS_COLLECTION, APPLICATIONS_COLLECTION, USERS_COLLECTION, PROFILES_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/user", tags=["user"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ✅ HELPER FUNCTION FOR JOB FORMATTING
def job_helper_with_id(job) -> dict:
    """Format job with both _id and id for frontend compatibility"""
    job_id = str(job["_id"])
    return {
        "_id": job_id,
        "id": job_id,  # Frontend expects 'id'
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "type": job["type"],
        "salary": job.get("salary"),
        "description": job["description"],
        "requirements": job["requirements"],
        "benefits": job.get("benefits"),
        "skills": job.get("skills", []),
        "status": job.get("status", "active"),
        "experience_level": job.get("experience_level"),
        "posted_date": job["posted_date"],
        "applications_count": job.get("applications_count", 0),
        "experience": job.get("experience_level"),
        "postedDate": job["posted_date"].isoformat() if job.get("posted_date") else None
    }


# ✅ 1. JOB RECOMMENDATIONS
@router.get("/recommended-jobs")
async def get_recommended_jobs(
    token: str = Depends(oauth2_scheme),
    limit: int = Query(10, le=50)
):
    """Get personalized job recommendations based on user profile"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user profile
    profile = await profiles_collection.find_one({"user_id": str(user["_id"])})
    
    # Build recommendation query
    query = {"status": "active"}
    
    if profile:
        # Match based on skills
        if profile.get("skills"):
            query["skills"] = {"$in": profile["skills"]}
        
        # Match based on experience level
        elif profile.get("experience"):
            query["experience_level"] = profile["experience"]
    
    # Get recommended jobs
    cursor = jobs_collection.find(query).sort("posted_date", -1).limit(limit)
    jobs = await cursor.to_list(length=limit)
    
    return [job_helper_with_id(job) for job in jobs]


# ✅ 2. ADVANCED JOB SEARCH (Main search endpoint for frontend)
@router.get("/search-jobs")
async def advanced_job_search(
    search: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    experience: Optional[str] = None,
    skills: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    """Advanced job search - Main endpoint for jobs.html"""
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Build query
    query = {"status": "active"}
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    if job_type:
        query["type"] = job_type
    
    if experience:
        query["experience_level"] = experience
    
    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        query["skills"] = {"$in": skill_list}
    
    # Get jobs
    cursor = jobs_collection.find(query).skip(skip).limit(limit).sort("posted_date", -1)
    jobs = await cursor.to_list(length=limit)
    
    # Get total count
    total = await jobs_collection.count_documents(query)
    
    return {
        "jobs": [job_helper_with_id(job) for job in jobs],
        "total": total,
        "page": skip // limit + 1,
        "pages": (total + limit - 1) // limit
    }


# ✅ 3. APPLICATION STATUS CHECK
@router.get("/application-status/{job_id}")
async def check_application_status(
    job_id: str,
    token: str = Depends(oauth2_scheme)
):
    """Check if user has applied to a specific job"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if application exists
    application = await applications_collection.find_one({
        "user_id": str(user["_id"]),
        "job_id": job_id
    })
    
    if application:
        return {
            "has_applied": True,
            "status": application.get("status"),
            "applied_at": application.get("applied_at"),
            "application_id": str(application["_id"])
        }
    
    return {"has_applied": False}


# ✅ 4. USER ACTIVITY TIMELINE
@router.get("/activity-timeline")
async def get_user_activity(
    token: str = Depends(oauth2_scheme),
    limit: int = Query(20, le=100)
):
    """Get user's recent activity (applications, saved jobs)"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    # Get recent applications
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    recent_apps = await applications_collection.find(
        {"user_id": user_id}
    ).sort("applied_at", -1).limit(limit).to_list(length=limit)
    
    # Get recent saved jobs
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    recent_saved = await saved_jobs_collection.find(
        {"user_id": user_id}
    ).sort("saved_at", -1).limit(limit).to_list(length=limit)
    
    # Combine activities
    activities = []
    
    for app in recent_apps:
        activities.append({
            "type": "application",
            "job_title": app.get("job_title"),
            "company": app.get("job_company"),
            "status": app.get("status"),
            "date": app.get("applied_at"),
            "id": str(app["_id"])
        })
    
    for saved in recent_saved:
        activities.append({
            "type": "saved",
            "job_title": saved.get("title"),
            "company": saved.get("company"),
            "date": saved.get("saved_at"),
            "id": str(saved["_id"])
        })
    
    # Sort by date
    activities.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
    
    return {"activities": activities[:limit]}


# ✅ 5. SIMILAR JOBS
@router.get("/similar-jobs/{job_id}")
async def get_similar_jobs(
    job_id: str,
    limit: int = Query(5, le=20)
):
    """Get similar jobs based on current job"""
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    try:
        # Get current job
        current_job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not current_job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Find similar jobs
        query = {
            "_id": {"$ne": ObjectId(job_id)},
            "status": "active",
            "$or": [
                {"skills": {"$in": current_job.get("skills", [])}},
                {"location": current_job.get("location")},
                {"type": current_job.get("type")},
                {"company": current_job.get("company")}
            ]
        }
        
        cursor = jobs_collection.find(query).limit(limit)
        similar_jobs = await cursor.to_list(length=limit)
        
        return [job_helper_with_id(job) for job in similar_jobs]
        
    except Exception as e:
        logger.error(f"Error getting similar jobs: {e}")
        return []


# ✅ 6. PROFILE COMPLETION STATUS (Detailed)
@router.get("/profile-completion-status")
async def get_profile_completion_status(token: str = Depends(oauth2_scheme)):
    """Get detailed profile completion status"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    profile = await profiles_collection.find_one({"user_id": str(user["_id"])})
    
    if not profile:
        return {
            "completed": False,
            "percentage": 0,
            "missing_fields": ["full_name", "phone", "location", "experience", "education", "skills", "about"]
        }
    
    # Calculate completion
    required_fields = ["full_name", "phone", "location", "experience", "education", "skills", "about"]
    completed_fields = []
    missing_fields = []
    
    for field in required_fields:
        value = profile.get(field)
        if value and (not isinstance(value, list) or len(value) > 0):
            completed_fields.append(field)
        else:
            missing_fields.append(field)
    
    percentage = int((len(completed_fields) / len(required_fields)) * 100)
    
    return {
        "completed": percentage >= 70,
        "percentage": percentage,
        "completed_fields": completed_fields,
        "missing_fields": missing_fields,
        "has_cv": profile.get("cv_uploaded", False)
    }


# ✅ 7. EXPORT USER DATA (GDPR)
@router.get("/export-data")
async def export_user_data(token: str = Depends(oauth2_scheme)):
    """Export all user data (GDPR compliance)"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    # Get all user data
    profile = await profiles_collection.find_one({"user_id": user_id})
    applications = await applications_collection.find({"user_id": user_id}).to_list(length=None)
    saved_jobs = await saved_jobs_collection.find({"user_id": user_id}).to_list(length=None)
    
    # Convert ObjectIds to strings
    def clean_doc(doc):
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    return {
        "user": {
            "email": user.get("email"),
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "created_at": user.get("created_at").isoformat() if user.get("created_at") else None
        },
        "profile": clean_doc(profile) if profile else None,
        "applications": [{
            "job_title": app.get("job_title"),
            "company": app.get("job_company"),
            "status": app.get("status"),
            "applied_at": app.get("applied_at").isoformat() if app.get("applied_at") else None
        } for app in applications],
        "saved_jobs": [{
            "title": job.get("title"),
            "company": job.get("company"),
            "saved_at": job.get("saved_at").isoformat() if job.get("saved_at") else None
        } for job in saved_jobs]
    }


# ✅ 8. NOTIFICATION PREFERENCES
@router.post("/notification-preferences")
async def update_notification_preferences(
    email_notifications: bool,
    job_alerts: bool,
    application_updates: bool,
    marketing_emails: bool = False,
    weekly_digest: bool = False,
    token: str = Depends(oauth2_scheme)
):
    """Update user notification preferences"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update preferences
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "notification_preferences": {
                "email_notifications": email_notifications,
                "job_alerts": job_alerts,
                "application_updates": application_updates,
                "marketing_emails": marketing_emails,
                "weekly_digest": weekly_digest,
                "updated_at": datetime.utcnow()
            }
        }}
    )
    
    return {
        "success": True,
        "message": "Notification preferences updated"
    }


# ✅ 9. JOB ALERT SUBSCRIPTIONS
@router.post("/job-alerts")
async def create_job_alert(
    keywords: List[str],
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    frequency: str = "daily",
    token: str = Depends(oauth2_scheme)
):
    """Create a job alert subscription"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create job alert
    job_alert = {
        "user_id": str(user["_id"]),
        "keywords": keywords,
        "location": location,
        "job_type": job_type,
        "frequency": frequency,
        "active": True,
        "created_at": datetime.utcnow(),
        "last_sent": None
    }
    
    # Store in user document
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$push": {"job_alerts": job_alert}}
    )
    
    return {
        "success": True,
        "message": "Job alert created successfully",
        "alert": job_alert
    }


# ✅ 10. BULK SAVE JOBS (Was missing from my previous version)
@router.post("/bulk-save-jobs")
async def bulk_save_jobs(
    job_ids: List[str],
    token: str = Depends(oauth2_scheme)
):
    """Save multiple jobs at once"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    saved_count = 0
    
    for job_id in job_ids:
        # Check if already saved
        existing = await saved_jobs_collection.find_one({
            "user_id": user_id,
            "job_id": job_id
        })
        
        if existing:
            continue
        
        # Get job details
        try:
            job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
            if job:
                saved_job_doc = {
                    "user_id": user_id,
                    "job_id": job_id,
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "type": job.get("type"),
                    "salary": job.get("salary"),
                    "saved_at": datetime.utcnow()
                }
                await saved_jobs_collection.insert_one(saved_job_doc)
                saved_count += 1
        except Exception as e:
            logger.error(f"Error saving job {job_id}: {e}")
            continue
    
    return {
        "success": True,
        "saved_count": saved_count,
        "message": f"{saved_count} jobs saved successfully"
    }