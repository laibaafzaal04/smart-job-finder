# app/routes/matching.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from typing import Optional

from app.database import get_collection
from app.utils.security import decode_token

router = APIRouter(prefix="/api/matching", tags=["matching"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.get("/job-match-score/{job_id}")
async def calculate_job_match_score(
    job_id: str,
    token: str = Depends(oauth2_scheme)
):
    """
    Calculate how well a user matches a job (0-100%)
    
    - **Skill Match**: 70% weight
    - **Experience Match**: 20% weight
    - **Location Match**: 10% weight
    """
    # Decode token and get user
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_email = payload.get("sub")
    
    # Get collections
    users_collection = get_collection("users")
    profiles_collection = get_collection("profiles")
    jobs_collection = get_collection("jobs")
    
    # Get user
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get profile
    profile = await profiles_collection.find_one({"user_id": str(user["_id"])})
    if not profile:
        return {
            "match_score": 0.0,
            "reason": "No profile found. Please complete your profile.",
            "matched_skills": [],
            "total_job_skills": 0,
            "matched_count": 0,
            "experience_match": False,
            "location_match": False
        }
    
    # Get job
    try:
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # ✅ SKILL MATCHING ALGORITHM
    user_skills = set(profile.get("skills", []))
    job_skills = set(job.get("skills", []))
    
    if not job_skills:
        return {
            "match_score": 50.0,
            "reason": "No skills specified for this job",
            "matched_skills": [],
            "total_job_skills": 0,
            "matched_count": 0,
            "experience_match": False,
            "location_match": False
        }
    
    matched_skills = user_skills.intersection(job_skills)
    skill_match_percentage = (len(matched_skills) / len(job_skills)) * 100 if job_skills else 0
    
    # ✅ EXPERIENCE LEVEL MATCH
    experience_match = 0
    user_exp = profile.get("experience", "").lower()
    job_exp = str(job.get("experience_level", "")).lower()
    
    if user_exp and job_exp and user_exp == job_exp:
        experience_match = 20
    
    # ✅ LOCATION MATCH
    location_match = 0
    user_location = profile.get("location", "").lower()
    job_location = job.get("location", "").lower()
    
    if user_location and job_location and user_location in job_location:
        location_match = 10
    
    # Calculate total score (max 100)
    total_score = min(
        skill_match_percentage * 0.7 + experience_match + location_match,
        100
    )
    
    return {
        "match_score": round(total_score, 1),
        "matched_skills": list(matched_skills),
        "missing_skills": list(job_skills - user_skills),
        "total_job_skills": len(job_skills),
        "matched_count": len(matched_skills),
        "experience_match": experience_match > 0,
        "location_match": location_match > 0,
        "breakdown": {
            "skill_score": round(skill_match_percentage * 0.7, 1),
            "experience_score": experience_match,
            "location_score": location_match
        }
    }