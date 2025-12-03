from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime
    audio_file: Optional[str] = None  # Path to audio chunk if available


class DatingProfile(BaseModel):
    """Extracted dating profile from conversation"""
    name: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    interests: List[str] = []
    looking_for: Optional[str] = None
    about_me: Optional[str] = None
    ideal_partner: Optional[str] = None
    fun_facts: List[str] = []
    conversation_style: Optional[str] = None


class ConversationSession(BaseModel):
    """Full conversation session data"""
    session_id: str
    user_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    messages: List[ConversationMessage] = []
    profile: Optional[DatingProfile] = None
    voice_clone_id: Optional[str] = None
    audio_recording_path: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed


class StartConversationRequest(BaseModel):
    user_id: Optional[str] = None


class StartConversationResponse(BaseModel):
    session_id: str
    websocket_url: str

