# app/routes/applications.py
from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import logging
from typing import List, Optional
from bson import ObjectId

# Add these imports
from app.utils.email_service import email_service

from app.models.application import (
    ApplicationCreate, 
    ApplicationResponse, 
    ApplicationUpdate,
    ApplicationStatus
)
from app.database import get_collection, APPLICATIONS_COLLECTION, JOBS_COLLECTION, USERS_COLLECTION, PROFILES_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/applications", tags=["applications"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def application_helper(app) -> dict:
    return {
        "_id": str(app["_id"]),
        "job_id": app.get("job_id", ""),
        "job_title": app.get("job_title", ""),
        "job_company": app.get("job_company", ""),
        "user_id": app.get("user_id", ""),
        "user_name": app.get("user_name", ""),
        "user_email": app.get("user_email", ""),
        "user_phone": app.get("user_phone", ""),
        "cover_letter": app.get("cover_letter", ""),
        "resume_url": app.get("resume_url"),
        "portfolio_url": app.get("portfolio_url"),
        "linkedin_url": app.get("linkedin_url"),
        "status": app.get("status", "pending"),
        "applied_at": app.get("applied_at", datetime.utcnow()),
        "reviewed_at": app.get("reviewed_at"),
        "reviewed_by": app.get("reviewed_by"),
        "notes": app.get("notes")
    }

# In the apply_for_job function in applications.py
@router.post("/apply", response_model=ApplicationResponse)
async def apply_for_job(
    application_data: ApplicationCreate, 
    token: str = Depends(oauth2_scheme),
    background_tasks: BackgroundTasks = BackgroundTasks()  # Add this
):
    """User applies for a job"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_email = payload.get("sub")
    role = payload.get("role")
    
    # Only job seekers can apply
    if role != "job_seeker":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only job seekers can apply for jobs"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user profile for phone number
    profile = await profiles_collection.find_one({"user_id": str(user["_id"])})
    
    # Validate job ID
    job_id = application_data.job_id
    if not job_id or job_id == "undefined" or job_id == "null":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job ID is required"
        )
    
    # Try to find the job - handle both ObjectId and string IDs
    job = None
    try:
        # Try to convert to ObjectId
        from bson import ObjectId
        if len(job_id) == 24:  # ObjectId should be 24 characters
            job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
        else:
            # Try to find by string ID or other fields
            job = await jobs_collection.find_one({"$or": [
                {"_id": ObjectId(job_id)},
                {"id": job_id},
                {"title": {"$regex": job_id, "$options": "i"}}
            ]})
    except Exception as e:
        # If ObjectId conversion fails, try to find by other means
        print(f"ObjectId conversion failed: {e}")
        job = await jobs_collection.find_one({"$or": [
            {"id": job_id},
            {"title": {"$regex": job_id, "$options": "i"}}
        ]})
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found with ID: {job_id}"
        )
    
    if job.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is not currently accepting applications"
        )
    
    # Check if already applied
    existing_application = await applications_collection.find_one({
        "job_id": str(job["_id"]) if "_id" in job else job_id,
        "user_id": str(user["_id"])
    })
    
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for this job"
        )
    
    now = datetime.utcnow()
    
    # Get job ID as string
    job_id_str = str(job["_id"]) if "_id" in job else job_id
    
    # Create application document
    application_doc = {
        "job_id": job_id_str,
        "job_title": job.get("title", ""),
        "job_company": job.get("company", ""),
        "user_id": str(user["_id"]),
        "user_name": user.get("full_name", ""),
        "user_email": user_email,
        "user_phone": profile.get("phone") if profile else None,
        "cover_letter": application_data.cover_letter,
        "resume_url": application_data.resume_url,
        "portfolio_url": application_data.portfolio_url,
        "linkedin_url": application_data.linkedin_url,
        "status": application_data.status,
        "applied_at": now,
        "reviewed_at": None,
        "reviewed_by": None,
        "notes": None
    }
    
    # Insert application
    result = await applications_collection.insert_one(application_doc)
    
    # Get created application
    created_app = await applications_collection.find_one({"_id": result.inserted_id})
    
    if not created_app:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application"
        )
    
    # Update applications count in job
    try:
        if "_id" in job:
            await jobs_collection.update_one(
                {"_id": job["_id"]},
                {"$inc": {"applications_count": 1}}
            )
    except Exception as e:
        print(f"Failed to update applications count: {e}")
    
    try:
        background_tasks.add_task(
            email_service.send_application_confirmation,
            to_email=user_email,
            user_name=user.get("full_name", ""),
            job_title=job.get("title", ""),
            company=job.get("company", "")
        )
    except Exception as e:
        logger.error(f"Failed to queue confirmation email: {e}")
     
    return ApplicationResponse(**application_helper(created_app))

# Get applications for admin's jobs
@router.get("/admin/applicants", response_model=List[ApplicationResponse])
async def get_admin_applicants(
    token: str = Depends(oauth2_scheme),
    status_filter: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    job_id: Optional[str] = Query(None, description="Filter by specific job")
):
    """Get all applicants for jobs posted by the current admin"""
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
            detail="Only admins can view applicants"
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
    
    # Build query for admin's jobs
    jobs_query = {"posted_by": str(admin_user["_id"])}
    if job_id:
        try:
            jobs_query["_id"] = ObjectId(job_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid job ID"
            )
    
    # Get admin's job IDs
    admin_jobs = await jobs_collection.find(jobs_query).to_list(length=100)
    admin_job_ids = [str(job["_id"]) for job in admin_jobs]
    
    if not admin_job_ids:
        return []
    
    # Build applications query
    apps_query = {"job_id": {"$in": admin_job_ids}}
    if status_filter:
        apps_query["status"] = status_filter
    
    # Get applications for admin's jobs
    cursor = applications_collection.find(apps_query).sort("applied_at", -1)
    applications = await cursor.to_list(length=100)
    
    return [ApplicationResponse(**application_helper(app)) for app in applications]

# CORRECTED SECTION - Replace lines 280-310 in your applications.py

@router.put("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: str,
    update_data: ApplicationUpdate,
    token: str = Depends(oauth2_scheme),
    background_tasks: BackgroundTasks = None  # ✅ FIXED: Optional parameter
):
    """Update application status (admin only)"""
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
            detail="Only admins can update application status"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": admin_email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    try:
        # Convert application_id to ObjectId
        app_object_id = ObjectId(application_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid application ID"
        )
    
    # Get application
    application = await applications_collection.find_one({"_id": app_object_id})
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if application belongs to admin's job
    job = await jobs_collection.find_one({
        "_id": ObjectId(application["job_id"]),
        "posted_by": str(admin_user["_id"])
    })
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this application"
        )
    
    now = datetime.utcnow()
    
    # Prepare update data
    update_doc = update_data.dict(exclude_none=True)
    update_doc["reviewed_at"] = now
    update_doc["reviewed_by"] = admin_user["email"]
    
    # Update application
    await applications_collection.update_one(
        {"_id": app_object_id},
        {"$set": update_doc}
    )
    
    # Get updated application
    updated_app = await applications_collection.find_one({"_id": app_object_id})
    
    # ✅ FIXED: Send status update email with proper indentation
    if update_data.status and background_tasks:
        application_user = await users_collection.find_one({"_id": ObjectId(application["user_id"])})
        if application_user:
            try:
                background_tasks.add_task(
                    email_service.send_application_status_update,
                    to_email=application_user["email"],
                    user_name=application_user.get("full_name", ""),
                    job_title=application.get("job_title", ""),
                    company=application.get("job_company", ""),
                    new_status=update_data.status
                )
            except Exception as e:
                logger.error(f"Failed to queue status update email: {e}")
    
    return ApplicationResponse(**application_helper(updated_app))

# Add this to app/routes/applications.py
@router.get("/my-applications", response_model=List[ApplicationResponse])
async def get_my_applications(token: str = Depends(oauth2_scheme)):
    """Get current user's applications"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)
    applications_collection = get_collection(APPLICATIONS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's applications
    cursor = applications_collection.find({"user_id": str(user["_id"])}).sort("applied_at", -1)
    applications = await cursor.to_list(length=100)
    
    return [ApplicationResponse(**application_helper(app)) for app in applications]

# Get application statistics for admin dashboard
@router.get("/admin/stats")
async def get_application_stats(token: str = Depends(oauth2_scheme)):
    """Get application statistics for admin dashboard"""
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
            detail="Only admins can view application stats"
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
    
    # Get admin's job IDs
    admin_jobs = await jobs_collection.find({"posted_by": str(admin_user["_id"])}).to_list(length=100)
    admin_job_ids = [str(job["_id"]) for job in admin_jobs]
    
    if not admin_job_ids:
        return {
            "total_applications": 0,
            "pending_applications": 0,
            "reviewed_applications": 0,
            "accepted_applications": 0,
            "rejected_applications": 0
        }
    
    # Get application counts by status
    pipeline = [
        {"$match": {"job_id": {"$in": admin_job_ids}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    status_counts = await applications_collection.aggregate(pipeline).to_list(length=10)
    
    # Format results
    stats = {
        "total_applications": 0,
        "pending_applications": 0,
        "reviewed_applications": 0,
        "accepted_applications": 0,
        "rejected_applications": 0
    }
    
    for count in status_counts:
        status = count["_id"]
        count_val = count["count"]
        stats["total_applications"] += count_val
        
        if status == "pending":
            stats["pending_applications"] = count_val
        elif status == "reviewed" or status == "shortlisted":
            stats["reviewed_applications"] += count_val
        elif status == "accepted":
            stats["accepted_applications"] = count_val
        elif status == "rejected":
            stats["rejected_applications"] = count_val
    
    return stats