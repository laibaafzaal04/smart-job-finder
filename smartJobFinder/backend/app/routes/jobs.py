from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import logging
from typing import Optional, List
from bson import ObjectId

from app.models.job import JobCreate, JobUpdate, JobResponse, JobStatus, JobType, ExperienceLevel
from app.database import get_collection, JOBS_COLLECTION, USERS_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def job_helper(job) -> dict:
    """Helper function with BOTH _id and id for frontend compatibility"""
    job_id = str(job["_id"])
    return {
        "_id": job_id,
        "id": job_id,  # ✅ ADD THIS - Frontend expects 'id' field
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
        "application_deadline": job.get("application_deadline"),
        "posted_by": job.get("posted_by"),
        "posted_by_email": job.get("posted_by_email", ""),
        "posted_by_name": job.get("posted_by_name", ""),
        "posted_date": job["posted_date"],
        "applications_count": job.get("applications_count", 0),
        # Frontend compatibility fields
        "experience": job.get("experience_level"),
        "postedDate": job["posted_date"].isoformat() if job.get("posted_date") else None
    }

# Create job (Admin only)
@router.post("/create", response_model=JobResponse)
async def create_job(job_data: JobCreate, token: str = Depends(oauth2_scheme)):
    """Create a new job (Admin only)"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create jobs"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    now = datetime.utcnow()
    
    # Create job document with owner info
    job_doc = {
        **job_data.dict(),
        "posted_by": str(admin_user["_id"]),
        "posted_by_email": admin_user["email"],
        "posted_by_name": admin_user["full_name"],
        "posted_date": now,
        "applications_count": 0,
        "created_at": now,
        "updated_at": now
    }
    
    # Insert job
    result = await jobs_collection.insert_one(job_doc)
    
    # Get created job
    created_job = await jobs_collection.find_one({"_id": result.inserted_id})
    
    if not created_job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )
    
    return JobResponse(**job_helper(created_job))

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    search: Optional[str] = Query(None, description="Search by title, company, or skills"),
    location: Optional[str] = Query(None, description="Filter by location"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    experience_level: Optional[ExperienceLevel] = Query(None, description="Filter by experience level"),
    skills: Optional[str] = Query(None, description="Filter by skills (comma-separated)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all active jobs with FULL-TEXT SEARCH"""
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    query = {"status": JobStatus.ACTIVE}
    
    # ✅ USE TEXT SEARCH instead of regex
    if search:
        query["$text"] = {"$search": search}
    
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    if job_type:
        query["type"] = job_type
    
    if experience_level:
        query["experience_level"] = experience_level
    
    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        query["skills"] = {"$in": skill_list}
    
    # ✅ SORT by text score when searching
    sort_criteria = [("posted_date", -1)]
    if search:
        sort_criteria.insert(0, ("score", {"$meta": "textScore"}))
        query["score"] = {"$meta": "textScore"}
    
    cursor = jobs_collection.find(query).skip(skip).limit(limit).sort(sort_criteria)
    jobs = await cursor.to_list(length=limit)
    
    return [JobResponse(**job_helper(job)) for job in jobs]

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str):
    """Get a specific job by ID (public)"""
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Validate job_id
    if not job_id or job_id.lower() in ["undefined", "null", "none"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job ID is required"
        )
    
    try:
        # Try to find by ObjectId first
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    except:
        # If ObjectId conversion fails, return not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(**job_helper(job))

# Get jobs by logged-in admin (private endpoint)
@router.get("/admin/my-jobs", response_model=List[JobResponse])
async def get_my_jobs(token: str = Depends(oauth2_scheme)):
    """Get jobs posted by the current admin"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get jobs posted by this admin
    cursor = jobs_collection.find({"posted_by": str(admin_user["_id"])}).sort("posted_date", -1)
    jobs = await cursor.to_list(length=100)
    
    return [JobResponse(**job_helper(job)) for job in jobs]

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, job_data: JobUpdate, token: str = Depends(oauth2_scheme)):
    """Update a job (Admin can only update their own jobs)"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update jobs"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Convert job_id to ObjectId
        object_id = ObjectId(job_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    # Check if job exists and belongs to this admin
    existing_job = await jobs_collection.find_one({
        "_id": object_id,
        "posted_by": str(admin_user["_id"])
    })
    
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or you don't have permission to edit this job"
        )
    
    # Update job
    update_data = job_data.dict(exclude_none=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await jobs_collection.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    # Get updated job
    updated_job = await jobs_collection.find_one({"_id": object_id})
    
    return JobResponse(**job_helper(updated_job))

@router.get("/admin/stats/count")
async def get_admin_jobs_count(token: str = Depends(oauth2_scheme)):
    """Get jobs count statistics for the current admin"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Count jobs for this admin
    total_jobs = await jobs_collection.count_documents({"posted_by": str(admin_user["_id"])})
    active_jobs = await jobs_collection.count_documents({
        "posted_by": str(admin_user["_id"]),
        "status": "active"
    })
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs
    }

@router.get("/admin/{job_id}", response_model=JobResponse)
async def get_admin_job_by_id(job_id: str, token: str = Depends(oauth2_scheme)):
    """Get a specific job by ID for admin editing (checks ownership)"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    if not job_id or job_id.lower() == "undefined":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job ID is required and cannot be undefined"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Convert job_id to ObjectId
        object_id = ObjectId(job_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job ID format: {str(e)}"
        )
    
    # Get job with ownership check
    job = await jobs_collection.find_one({
        "_id": object_id,
        "posted_by": str(admin_user["_id"])
    })
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or you don't have permission to view this job"
        )
    
    return JobResponse(**job_helper(job))

@router.delete("/{job_id}")
async def delete_job(job_id: str, token: str = Depends(oauth2_scheme)):
    """Delete a job (Admin can only delete their own jobs)"""
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    email = payload.get("sub")
    role = payload.get("role")
    
    if role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete jobs"
        )
    
    if not job_id or job_id.lower() == "undefined":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job ID is required and cannot be undefined"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get admin user
    admin_user = await users_collection.find_one({"email": email})
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Convert job_id to ObjectId
        object_id = ObjectId(job_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid job ID format: {str(e)}"
        )
    
    # Check if job exists and belongs to this admin
    existing_job = await jobs_collection.find_one({
        "_id": object_id,
        "posted_by": str(admin_user["_id"])
    })
    
    if not existing_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or you don't have permission to delete this job"
        )
    
    # Delete job
    await jobs_collection.delete_one({"_id": object_id})
    
    return {"message": "Job deleted successfully"}