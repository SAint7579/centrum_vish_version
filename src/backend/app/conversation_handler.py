"""
Conversation handler for Eleven Labs Conversational AI
Manages the conversation flow and audio recording
"""
import json
import asyncio
import uuid
import wave
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import httpx

from app.config import (
    ELEVEN_LABS_API_KEY, 
    ELEVENLABS_AGENT_ID,
    RECORDINGS_DIR,
    CONVERSATIONS_DIR
)
from app.models import (
    ConversationSession, 
    ConversationMessage, 
    MessageRole,
    DatingProfile
)


class ConversationManager:
    """Manages a single conversation session"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
            profile=DatingProfile()  # Initialize empty profile
        )
        self.audio_chunks: list[bytes] = []
        self.is_active = False
        
    def add_message(self, role: MessageRole, content: str, audio_file: Optional[str] = None):
        """Add a message to the conversation"""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            audio_file=audio_file
        )
        self.session.messages.append(message)
    
    def update_profile(self, **kwargs):
        """Update the dating profile with new information"""
        if not self.session.profile:
            self.session.profile = DatingProfile()
        
        profile = self.session.profile
        
        # Update fields
        if kwargs.get("age"):
            profile.age = kwargs["age"]
        if kwargs.get("about_me"):
            profile.about_me = kwargs["about_me"]
        if kwargs.get("looking_for"):
            profile.looking_for = kwargs["looking_for"]
        
        print(f"📝 Profile updated: {kwargs}")
        return profile
        
    def add_audio_chunk(self, chunk: bytes):
        """Add an audio chunk from user's speech"""
        self.audio_chunks.append(chunk)
        
    def save_audio_recording(self) -> str:
        """Save all audio chunks as a WAV file"""
        if not self.audio_chunks:
            return None
            
        audio_path = RECORDINGS_DIR / f"{self.session_id}.wav"
        
        # Combine all chunks
        all_audio = b''.join(self.audio_chunks)
        
        # Save as WAV (assuming 16kHz, 16-bit, mono - adjust if needed)
        with wave.open(str(audio_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(all_audio)
            
        self.session.audio_recording_path = str(audio_path)
        return str(audio_path)
    
    def save_conversation_json(self) -> str:
        """Save conversation to JSON file"""
        json_path = CONVERSATIONS_DIR / f"{self.session_id}.json"
        
        # Convert session to dict for JSON serialization
        session_dict = self.session.model_dump(mode='json')
        
        with open(json_path, 'w') as f:
            json.dump(session_dict, f, indent=2, default=str)
            
        return str(json_path)
    
    def end_session(self):
        """End the conversation session and save everything"""
        self.session.ended_at = datetime.utcnow()
        self.session.status = "completed"
        self.is_active = False
        
        # Save audio and conversation
        audio_path = self.save_audio_recording()
        json_path = self.save_conversation_json()
        
        return {
            "audio_path": audio_path,
            "json_path": json_path,
            "session": self.session,
            "profile": self.session.profile
        }


async def get_signed_url() -> dict:
    """Get a signed URL for Eleven Labs Conversational AI"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url",
            params={"agent_id": ELEVENLABS_AGENT_ID},
            headers={"xi-api-key": ELEVEN_LABS_API_KEY}
        )
        print(f"🔗 Signed URL response: {response.status_code}")
        response.raise_for_status()
        return response.json()


def create_session() -> ConversationManager:
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())
    return ConversationManager(session_id=session_id)


# Store active sessions
active_sessions: dict[str, ConversationManager] = {}


def get_session(session_id: str) -> Optional[ConversationManager]:
    """Get an active session by ID"""
    return active_sessions.get(session_id)


def register_session(manager: ConversationManager):
    """Register a session as active"""
    active_sessions[manager.session_id] = manager
    manager.is_active = True


def unregister_session(session_id: str):
    """Remove a session from active sessions"""
    if session_id in active_sessions:
        del active_sessions[session_id]
