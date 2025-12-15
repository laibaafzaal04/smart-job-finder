from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
from app.utils.email_service import email_service
import logging

from app.models.user import (
    UserRegister, 
    UserLogin, 
    UserResponse, 
    Token,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserRole
)
from app.utils.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    decode_token
)
from app.database import get_collection, USERS_COLLECTION
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Helper function to convert MongoDB document to dict - SIMPLIFIED
def user_helper(user) -> dict:
    return {
        "_id": str(user["_id"]),  # Convert ObjectId to string
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "has_cv": user.get("has_cv", False),
        "profile_completed": user.get("profile_completed", False),
        "created_at": user["created_at"]
    }

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Register a new user (regular or admin)"""
    users_collection = get_collection(USERS_COLLECTION)
    
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate admin code for admin registration
    role = UserRole.ADMIN if user_data.is_admin else UserRole.JOB_SEEKER
    
    if user_data.is_admin:
        if user_data.admin_code != settings.ADMIN_REGISTRATION_CODE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid admin registration code"
            )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user document
    now = datetime.utcnow()
    user_doc = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "password_hash": hashed_password,
        "role": role,
        "is_active": True,
        "is_verified": False,
        "has_cv": False,
        "profile_completed": False,
        "created_at": now,
        "updated_at": now,
        "last_login": None
    }
    
    # Insert user
    result = await users_collection.insert_one(user_doc)
    
    # Get created user
    created_user = await users_collection.find_one({"_id": result.inserted_id})
    
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user_data.email, "role": role}
    )
    
    # Prepare response
    user_dict = user_helper(created_user)
    user_response = UserResponse(**user_dict)
    
    # Determine message based on role
    message = "Admin account created successfully!" if user_data.is_admin else "Account created successfully!"
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response,
        "message": message
    }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login user or admin"""
    users_collection = get_collection(USERS_COLLECTION)
    
    # Find user by email
    user = await users_collection.find_one({"email": user_data.email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Check role if admin login is requested
    if user_data.is_admin and user["role"] not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login not allowed for this account"
        )
    
    # Verify password
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Update last login
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user_data.email, "role": user["role"]},
        remember_me=user_data.remember_me
    )
    
    # Prepare response
    user_dict = user_helper(user)
    user_response = UserResponse(**user_dict)
    
    # Determine message based on role
    message = "Admin login successful!" if user_data.is_admin else "Login successful!"
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response,
        "message": message
    }

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Send password reset email"""
    users_collection = get_collection(USERS_COLLECTION)
    
    # Check if user exists
    user = await users_collection.find_one({"email": request.email})
    
    if user:
        # Generate reset token (valid for 1 hour)
        reset_token = create_access_token(
            data={"sub": user["email"], "type": "password_reset"},
            remember_me=False  # 1 hour expiry
        )
        
        # Send email in background
        try:
            background_tasks.add_task(
                email_service.send_password_reset_email,
                to_email=user["email"],
                reset_token=reset_token,
                user_name=user["full_name"]
            )
            logger.info(f"Password reset email queued for {user['email']}")
        except Exception as e:
            logger.error(f"Failed to queue password reset email: {e}")
    
    # Always return success for security (don't reveal if email exists)
    return {
        "message": "If your email is registered, you will receive a reset link",
        "email": request.email
    }

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password with token"""
    # Decode token
    payload = decode_token(request.token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    email = payload.get("sub")
    token_type = payload.get("type")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    # Check token type (allow both temporarily for testing)
    if token_type not in ["password_reset", "access"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type for password reset"
        )
    
    users_collection = get_collection(USERS_COLLECTION)
    
    # Find user
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash new password
    hashed_password = get_password_hash(request.new_password)
    
    # Update password
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": hashed_password,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Password reset successfully"}


# Add this endpoint to your app/routes/auth.py file
# Place it AFTER the reset_password function and BEFORE the get_current_user function

@router.post("/verify-reset-token")
async def verify_reset_token(request: dict):
    """Verify if a reset token is valid (doesn't reset password, just checks token)"""
    token = request.get("token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is required"
        )
    
    # Decode token to check if it's valid
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    email = payload.get("sub")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format"
        )
    
    # Optionally verify user exists
    users_collection = get_collection(USERS_COLLECTION)
    user = await users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "valid": True,
        "message": "Token is valid",
        "email": email
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user info from token"""
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
    user = await users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user_helper(user))