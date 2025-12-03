"""
Eleven Labs Voice Cloning integration
"""
import httpx
from app.config import ELEVEN_LABS_API_KEY

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


async def create_voice_clone(user_id: str, audio_data: bytes, name: str = None) -> dict:
    """
    Create a voice clone from audio data using Eleven Labs API
    
    Args:
        user_id: User ID to use as voice name if name not provided
        audio_data: Raw audio bytes (WAV format)
        name: Optional name for the voice
    
    Returns:
        dict with voice_id and other metadata
    """
    voice_name = name or f"user_{user_id}"
    
    async with httpx.AsyncClient() as client:
        # Prepare multipart form data
        files = {
            "files": (f"{user_id}.wav", audio_data, "audio/wav")
        }
        data = {
            "name": voice_name,
            "description": f"Voice clone for Centrum user {user_id}",
            "labels": '{"user_id": "' + user_id + '", "source": "centrum"}'
        }
        
        response = await client.post(
            f"{ELEVENLABS_API_URL}/voices/add",
            headers={"xi-api-key": ELEVEN_LABS_API_KEY},
            files=files,
            data=data,
            timeout=120.0  # Voice cloning can take time
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Voice clone created: {result.get('voice_id')}")
            return {
                "success": True,
                "voice_id": result.get("voice_id"),
                "name": voice_name
            }
        else:
            print(f"❌ Voice clone failed: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }


async def get_voice(voice_id: str) -> dict:
    """Get voice details by ID"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ELEVENLABS_API_URL}/voices/{voice_id}",
            headers={"xi-api-key": ELEVEN_LABS_API_KEY}
        )
        
        if response.status_code == 200:
            return response.json()
        return None


async def delete_voice(voice_id: str) -> bool:
    """Delete a voice clone"""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{ELEVENLABS_API_URL}/voices/{voice_id}",
            headers={"xi-api-key": ELEVEN_LABS_API_KEY}
        )
        return response.status_code == 200

