from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    UploadFile,
    File,
    Form
)
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import logging
import os
import json
from typing import Optional, List
from bson import ObjectId

from app.models.profile import ProfileCreate, ProfileResponse
from app.database import get_collection, PROFILES_COLLECTION, USERS_COLLECTION
from app.utils.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# -------------------------
# Helper
# -------------------------
def profile_helper(profile) -> dict:
    return {
        "_id": str(profile["_id"]),
        "user_id": profile.get("user_id", ""),
        "full_name": profile.get("full_name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "location": profile.get("location", ""),
        "headline": profile.get("headline"),
        "about": profile.get("about"),
        "education": profile.get("education"),
        "experience": profile.get("experience"),
        "skills": profile.get("skills", []),
        "cv_uploaded": profile.get("cv_uploaded", False),
        "cv_filename": profile.get("cv_filename"),
        "profile_completed": profile.get("profile_completed", True),
        "profile_completion_percentage": profile.get("profile_completion_percentage", 0),
        "created_at": profile.get("created_at", datetime.utcnow()),
        "updated_at": profile.get("updated_at", datetime.utcnow()),
    }


# -------------------------
# Create / Update Profile (WITH FILE UPLOAD)
# -------------------------
@router.post("/create", response_model=ProfileResponse)
async def create_profile(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    location: str = Form(...),
    headline: Optional[str] = Form(None),
    about: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    skills: str = Form("[]"),  # JSON string
    cv_file: Optional[UploadFile] = File(None),
    token: str = Depends(oauth2_scheme)
):
    """Create or update user profile with optional CV upload"""

    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(401, "Invalid token")

    users_collection = get_collection(USERS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)

    # Validate user exists
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(404, "User not found")

    # Parse skills JSON
    try:
        skills_list = json.loads(skills) if skills else []
    except json.JSONDecodeError:
        skills_list = []

    # Check existing profile
    existing_profile = await profiles_collection.find_one(
        {"user_id": str(user["_id"])}
    )

    now = datetime.utcnow()

    # Handle CV file upload
    cv_uploaded = False
    cv_filename = None
    
    if cv_file and cv_file.filename:
        # Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx']
        file_ext = os.path.splitext(cv_file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(400, "Invalid file type. Only PDF, DOC, DOCX allowed")
        
        # Validate file size (5MB)
        content = await cv_file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(400, "File size exceeds 5MB limit")
        
        # Save file
        os.makedirs("uploads/cv", exist_ok=True)
        cv_filename = f"{str(user['_id'])}_{cv_file.filename}"
        filepath = os.path.join("uploads/cv", cv_filename)
        
        with open(filepath, "wb") as buffer:
            buffer.write(content)
        
        cv_uploaded = True
        logger.info(f"CV uploaded: {cv_filename}")

    profile_doc = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "location": location,
        "headline": headline,
        "about": about,
        "education": education,
        "experience": experience,
        "skills": skills_list,
        "cv_uploaded": cv_uploaded or (existing_profile and existing_profile.get("cv_uploaded", False)),
        "cv_filename": cv_filename or (existing_profile and existing_profile.get("cv_filename")),
        "profile_completed": True,
        "updated_at": now,
    }

    # Remove None values
    profile_doc = {k: v for k, v in profile_doc.items() if v is not None}

    # Update or Create profile
    if existing_profile:
        await profiles_collection.update_one(
            {"_id": existing_profile["_id"]},
            {"$set": profile_doc}
        )
        updated_profile = await profiles_collection.find_one(
            {"_id": existing_profile["_id"]}
        )
        logger.info(f"Profile updated for user: {user_email}")
    else:
        profile_doc.update({
            "user_id": str(user["_id"]),
            "created_at": now,
            "profile_completion_percentage": 0,
        })

        result = await profiles_collection.insert_one(profile_doc)
        updated_profile = await profiles_collection.find_one(
            {"_id": result.inserted_id}
        )
        logger.info(f"Profile created for user: {user_email}")

    # Update user flag
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"profile_completed": True, "updated_at": now}}
    )

    if not updated_profile:
        raise HTTPException(500, "Failed to save profile")

    return ProfileResponse(**profile_helper(updated_profile))


# -------------------------
# Upload CV (multipart form-data) - SEPARATE ENDPOINT
# -------------------------
@router.post("/upload-cv")
async def upload_cv(
    cv: UploadFile = File(...),
    token: str = Depends(oauth2_scheme)
):
    """Upload CV PDF/Doc file"""

    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(401, "Invalid token")

    users_collection = get_collection(USERS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)

    # Validate user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")

    # Ensure uploads/cv folder
    os.makedirs("uploads/cv", exist_ok=True)

    filename = f"{str(user['_id'])}_{cv.filename}"
    filepath = os.path.join("uploads/cv", filename)

    # Save file
    with open(filepath, "wb") as buffer:
        buffer.write(await cv.read())

    # Update profile DB
    await profiles_collection.update_one(
        {"user_id": str(user["_id"])},
        {"$set": {"cv_uploaded": True, "cv_filename": filename}}
    )

    return {
        "message": "CV uploaded successfully",
        "filename": filename
    }


# -------------------------
# Get My Profile
# -------------------------
@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(token: str = Depends(oauth2_scheme)):

    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(401, "Invalid token")

    users_collection = get_collection(USERS_COLLECTION)
    profiles_collection = get_collection(PROFILES_COLLECTION)

    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")

    profile = await profiles_collection.find_one({"user_id": str(user["_id"])})
    if not profile:
        raise HTTPException(404, "Profile not found")

    return ProfileResponse(**profile_helper(profile))


# -------------------------
# Check Profile Status
# -------------------------
@router.get("/check-status")
async def check_profile_status(token: str = Depends(oauth2_scheme)):

    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    email = payload.get("sub")
    users_collection = get_collection(USERS_COLLECTION)

    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")

    return {
        "profile_completed": user.get("profile_completed", False),
        "user_id": str(user["_id"]),
        "email": email
    }