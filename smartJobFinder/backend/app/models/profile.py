from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class ProfileBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    location: str
    headline: Optional[str] = None
    about: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[str]] = []
    cv_uploaded: bool = False
    cv_filename: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    _id: str
    user_id: str
    profile_completed: bool = True
    profile_completion_percentage: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
