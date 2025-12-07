from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

class SavedJobBase(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    type: str
    salary: Optional[str] = None

class SavedJobCreate(SavedJobBase):
    pass

class SavedJobResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    job_id: str
    title: str
    company: str
    location: str
    type: str
    salary: Optional[str] = None
    saved_at: datetime
    
    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }
        populate_by_name = True