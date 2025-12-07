from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import logging
from bson import ObjectId, errors

from app.models.saved_job import SavedJobCreate, SavedJobResponse
from app.database import get_collection, SAVED_JOBS_COLLECTION, USERS_COLLECTION, JOBS_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/saved-jobs", tags=["saved-jobs"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def saved_job_helper(saved_job) -> dict:
    """Helper function to format saved job document"""
    return {
        "_id": str(saved_job["_id"]),
        "user_id": saved_job.get("user_id", ""),
        "job_id": saved_job.get("job_id", ""),
        "title": saved_job.get("title", ""),
        "company": saved_job.get("company", ""),
        "location": saved_job.get("location", ""),
        "type": saved_job.get("type", ""),
        "salary": saved_job.get("salary"),
        "saved_at": saved_job.get("saved_at", datetime.utcnow())
    }

@router.get("/", response_model=list[SavedJobResponse])
async def get_saved_jobs(token: str = Depends(oauth2_scheme)):
    """Get all saved jobs for current user"""
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
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = str(user["_id"])
    
    # Get saved jobs for this user
    saved_jobs_cursor = saved_jobs_collection.find({"user_id": user_id}).sort("saved_at", -1)
    saved_jobs = await saved_jobs_cursor.to_list(length=None)
    
    return [SavedJobResponse(**saved_job_helper(job)) for job in saved_jobs]

@router.post("/", response_model=SavedJobResponse)
async def save_job(
    saved_job_data: SavedJobCreate,
    token: str = Depends(oauth2_scheme)
):
    """Save a job for current user"""
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
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    jobs_collection = get_collection(JOBS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = str(user["_id"])
    job_id = saved_job_data.job_id
    
    # Check if job exists
    try:
        job_object_id = ObjectId(job_id)
        job = await jobs_collection.find_one({"_id": job_object_id})
    except errors.InvalidId:
        job = await jobs_collection.find_one({"job_id": job_id})
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if already saved
    existing_saved_job = await saved_jobs_collection.find_one({
        "user_id": user_id,
        "job_id": job_id
    })
    
    if existing_saved_job:
        # Return existing saved job
        return SavedJobResponse(**saved_job_helper(existing_saved_job))
    
    # Create saved job document
    now = datetime.utcnow()
    saved_job_doc = {
        "user_id": user_id,
        "job_id": job_id,
        "title": saved_job_data.title,
        "company": saved_job_data.company,
        "location": saved_job_data.location,
        "type": saved_job_data.type,
        "salary": saved_job_data.salary,
        "saved_at": now
    }
    
    # Insert into database
    result = await saved_jobs_collection.insert_one(saved_job_doc)
    
    # Get the saved job
    saved_job = await saved_jobs_collection.find_one({"_id": result.inserted_id})
    
    if not saved_job:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save job"
        )
    
    return SavedJobResponse(**saved_job_helper(saved_job))

@router.delete("/{job_id}")
async def unsave_job(job_id: str, token: str = Depends(oauth2_scheme)):
    """Unsave/remove a job from saved jobs"""
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
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = str(user["_id"])
    
    # Delete saved job
    result = await saved_jobs_collection.delete_one({
        "user_id": user_id,
        "job_id": job_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved job not found"
        )
    
    return {
        "success": True,
        "message": "Job removed from saved jobs",
        "deleted_count": result.deleted_count
    }

@router.get("/check/{job_id}")
async def check_if_saved(job_id: str, token: str = Depends(oauth2_scheme)):
    """Check if a job is saved by current user"""
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
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = str(user["_id"])
    
    # Check if job is saved
    saved_job = await saved_jobs_collection.find_one({
        "user_id": user_id,
        "job_id": job_id
    })
    
    return {
        "is_saved": bool(saved_job),
        "job_id": job_id
    }

@router.get("/count")
async def get_saved_jobs_count(token: str = Depends(oauth2_scheme)):
    """Get count of saved jobs for current user"""
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
    saved_jobs_collection = get_collection(SAVED_JOBS_COLLECTION)
    
    # Get user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_id = str(user["_id"])
    
    # Count saved jobs
    count = await saved_jobs_collection.count_documents({"user_id": user_id})
    
    return {
        "user_id": user_id,
        "saved_jobs_count": count
    }