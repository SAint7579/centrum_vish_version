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
    ELEVENLABS_API_KEY, 
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
            started_at=datetime.utcnow()
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
            "session": self.session
        }


# Dating profile agent prompt
DATING_PROFILE_PROMPT = """You are a friendly and engaging conversation partner helping someone create their dating profile. Your goal is to have a natural, warm conversation that helps extract information for their profile while also capturing good voice samples for voice cloning.

Guidelines:
1. Be warm, friendly, and make the person feel comfortable
2. Ask open-ended questions that encourage longer responses (this helps with voice cloning)
3. Show genuine interest in their answers
4. Gently guide the conversation to cover these topics:
   - Their name and basic info
   - What they do for work/passion
   - Their hobbies and interests
   - What they're looking for in a partner
   - Fun facts or unique things about them
   - What their ideal date would be
   - Their sense of humor and personality

5. Occasionally ask them to elaborate or tell a story - this gets natural, expressive speech
6. Keep the conversation flowing naturally - don't make it feel like an interview
7. After covering the main topics (usually 5-10 minutes), wrap up warmly

Example conversation starters:
- "Hey! I'm excited to help you create your dating profile. Let's start easy - tell me your name and a little about yourself!"
- "What's something you're really passionate about?"
- "Tell me about your perfect weekend - paint me a picture!"

Remember: The goal is a fun, natural conversation that extracts profile info AND captures their authentic voice."""


async def get_signed_url() -> dict:
    """Get a signed URL for Eleven Labs Conversational AI"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url",
            params={"agent_id": ELEVENLABS_AGENT_ID},
            headers={"xi-api-key": ELEVENLABS_API_KEY}
        )
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

