from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from bson import ObjectId

class JobType(str, Enum):
    FULL_TIME = "Full-Time"
    PART_TIME = "Part-Time"
    INTERNSHIP = "Internship"
    CONTRACT = "Contract"
    REMOTE = "Remote"

class JobStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    EXECUTIVE = "executive"

class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    type: JobType
    salary: Optional[str] = None
    description: str
    requirements: str
    benefits: Optional[str] = None
    skills: List[str] = []
    status: JobStatus = JobStatus.ACTIVE
    experience_level: Optional[ExperienceLevel] = None
    application_deadline: Optional[datetime] = None
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Job title must be at least 2 characters')
        return v.strip()
    
    @validator('company')
    def validate_company(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Company name must be at least 2 characters')
        return v.strip()
    
    @validator('location')
    def validate_location(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Location must be at least 2 characters')
        return v.strip()

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    type: Optional[JobType] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[JobStatus] = None
    experience_level: Optional[ExperienceLevel] = None
    application_deadline: Optional[datetime] = None

class JobResponse(BaseModel):
    id: str = Field(alias="_id")
    title: str
    company: str
    location: str
    type: JobType
    salary: Optional[str] = None
    description: str
    requirements: str
    benefits: Optional[str] = None
    skills: List[str] = []
    status: JobStatus
    experience_level: Optional[ExperienceLevel] = None
    application_deadline: Optional[datetime] = None
    posted_by: str  # Admin user ID who posted the job
    posted_by_email: str  # Admin email for display
    posted_by_name: str  # Admin name for display
    posted_date: datetime
    applications_count: int = 0
    # Add these fields for frontend compatibility
    experience: Optional[str] = None
    postedDate: Optional[str] = None

    @validator('experience')
    def set_experience(cls, v, values):
        if v is None and 'experience_level' in values:
            return values['experience_level'].value if values['experience_level'] else None
        return v
    
    @validator('postedDate')
    def set_posted_date(cls, v, values):
        if v is None and 'posted_date' in values:
            # Format date as ISO string for frontend
            return values['posted_date'].isoformat() if values['posted_date'] else None
        return v
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }