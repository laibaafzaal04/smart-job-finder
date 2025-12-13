from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from groq import Groq

from app.database import get_collection
from app.utils.security import decode_token

router = APIRouter(prefix="/api/chatbot", tags=["AI Chatbot"])

# Initialize Groq client (FREE API)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Message]] = []

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None

async def get_current_user_from_header(authorization: str = Header(...)):
    """Extract user from Authorization header"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    users_collection = get_collection("users")
    user = await users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    authorization: str = Header(...)
):
    """
    Chat with AI assistant about job search, career advice, resume tips, etc.
    Uses Groq API (FREE)
    """
    try:
        # Get current user
        current_user = await get_current_user_from_header(authorization)
        
        # Get user profile for context
        profiles_collection = get_collection("profiles")
        user_profile = await profiles_collection.find_one({"user_id": str(current_user["_id"])})
        
        # Build context about user
        user_context = ""
        if user_profile:
            user_context = f"""
User Profile Context:
- Name: {user_profile.get('full_name', 'Not provided')}
- Current Position: {user_profile.get('current_position', 'Not provided')}
- Experience Level: {user_profile.get('experience_level', 'Not provided')}
- Skills: {', '.join(user_profile.get('skills', [])) if user_profile.get('skills') else 'Not provided'}
- Preferred Job Types: {', '.join(user_profile.get('preferred_job_types', [])) if user_profile.get('preferred_job_types') else 'Not provided'}
"""
        
        # System prompt for the AI
        system_prompt = f"""You are a helpful career assistant for Smart Job Finder, a job search platform. 
Your role is to help users with:
- Job search advice and strategies
- Resume and cover letter tips
- Interview preparation
- Career development guidance
- Answering questions about job applications
- Providing insights on job market trends

{user_context}

Be friendly, professional, and provide actionable advice. Keep responses concise but informative (max 3-4 paragraphs).
If the user asks about specific jobs, suggest they use the job search feature on the platform.
"""
        
        # Build conversation messages for Groq
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        for msg in chat_request.conversation_history[-10:]:  # Keep last 10 messages for context
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": chat_request.message
        })
        
        # Call Groq API (FREE & FAST)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",  # Free model - very capable
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        
        # Extract response text
        ai_response = chat_completion.choices[0].message.content
        
        # Save conversation to database
        conversations_collection = get_collection("chatbot_conversations")
        conversation_doc = {
            "user_id": str(current_user["_id"]),
            "messages": [msg.dict() for msg in chat_request.conversation_history] + [
                {"role": "user", "content": chat_request.message},
                {"role": "assistant", "content": ai_response}
            ],
            "timestamp": datetime.utcnow(),
            "model": "llama-3.3-70b-versatile"
        }
        result = await conversations_collection.insert_one(conversation_doc)
        
        return ChatResponse(
            response=ai_response,
            conversation_id=str(result.inserted_id)
        )
        
    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@router.get("/conversations")
async def get_user_conversations(
    authorization: str = Header(...),
    limit: int = 10
):
    """Get user's recent chatbot conversations"""
    try:
        current_user = await get_current_user_from_header(authorization)
        
        conversations_collection = get_collection("chatbot_conversations")
        cursor = conversations_collection.find(
            {"user_id": str(current_user["_id"])}
        ).sort("timestamp", -1).limit(limit)
        
        conversations = []
        async for conv in cursor:
            conv["_id"] = str(conv["_id"])
            conversations.append(conv)
        
        return {
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization: str = Header(...)
):
    """Delete a conversation"""
    try:
        from bson import ObjectId
        current_user = await get_current_user_from_header(authorization)
        
        conversations_collection = get_collection("chatbot_conversations")
        
        result = await conversations_collection.delete_one({
            "_id": ObjectId(conversation_id),
            "user_id": str(current_user["_id"])
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/chat/new")
async def start_new_conversation(
    authorization: str = Header(...)
):
    """Start a new conversation (clear history)"""
    try:
        current_user = await get_current_user_from_header(authorization)
        
        return {
            "message": "New conversation started",
            "user_id": str(current_user["_id"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")