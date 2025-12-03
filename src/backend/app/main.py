"""
Centrum Backend - Dating Profile Conversation API
"""
import json
import asyncio
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import websockets

from app.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, CONVERSATIONS_DIR, RECORDINGS_DIR
from app.models import StartConversationRequest, StartConversationResponse, MessageRole
from app.conversation_handler import (
    create_session,
    get_session,
    register_session,
    unregister_session,
    get_signed_url,
    ConversationManager,
    DATING_PROFILE_PROMPT
)

app = FastAPI(
    title="Centrum API",
    description="Dating Profile Conversation API with Voice Cloning",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Centrum API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/conversation/start", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """Start a new conversation session"""
    
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        raise HTTPException(
            status_code=500, 
            detail="Eleven Labs credentials not configured"
        )
    
    # Create new session
    manager = create_session()
    manager.user_id = request.user_id
    register_session(manager)
    
    return StartConversationResponse(
        session_id=manager.session_id,
        websocket_url=f"/api/conversation/{manager.session_id}/ws"
    )


@app.websocket("/api/conversation/{session_id}/ws")
async def conversation_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint that bridges the frontend to Eleven Labs Conversational AI
    
    Flow:
    1. Frontend connects to this WebSocket
    2. We connect to Eleven Labs WebSocket
    3. We relay messages between them while recording
    """
    await websocket.accept()
    
    manager = get_session(session_id)
    if not manager:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    eleven_ws = None
    
    try:
        # Get signed URL for Eleven Labs
        signed_url_data = await get_signed_url()
        signed_url = signed_url_data.get("signed_url")
        
        if not signed_url:
            await websocket.send_json({"type": "error", "message": "Failed to get Eleven Labs URL"})
            return
        
        # Connect to Eleven Labs
        eleven_ws = await websockets.connect(signed_url)
        
        # Send initial config to Eleven Labs
        init_message = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": DATING_PROFILE_PROMPT
                    }
                }
            }
        }
        await eleven_ws.send(json.dumps(init_message))
        
        # Notify frontend we're ready
        await websocket.send_json({
            "type": "ready",
            "session_id": session_id
        })
        
        async def forward_to_eleven():
            """Forward messages from frontend to Eleven Labs"""
            try:
                while True:
                    data = await websocket.receive()
                    
                    if "text" in data:
                        # Text message from frontend
                        msg = json.loads(data["text"])
                        
                        if msg.get("type") == "end_conversation":
                            # End the conversation
                            break
                        
                        await eleven_ws.send(data["text"])
                        
                    elif "bytes" in data:
                        # Audio data from frontend (user speaking)
                        audio_bytes = data["bytes"]
                        
                        # Store for voice cloning
                        manager.add_audio_chunk(audio_bytes)
                        
                        # Forward to Eleven Labs
                        await eleven_ws.send(audio_bytes)
                        
            except WebSocketDisconnect:
                pass
        
        async def forward_from_eleven():
            """Forward messages from Eleven Labs to frontend"""
            try:
                async for message in eleven_ws:
                    if isinstance(message, str):
                        # JSON message
                        msg_data = json.loads(message)
                        msg_type = msg_data.get("type")
                        
                        # Log conversation messages
                        if msg_type == "user_transcript":
                            text = msg_data.get("user_transcript", "")
                            if text:
                                manager.add_message(MessageRole.USER, text)
                                
                        elif msg_type == "agent_response":
                            text = msg_data.get("agent_response", "")
                            if text:
                                manager.add_message(MessageRole.AGENT, text)
                        
                        # Forward to frontend
                        await websocket.send_text(message)
                        
                    else:
                        # Binary audio data from agent
                        await websocket.send_bytes(message)
                        
            except websockets.exceptions.ConnectionClosed:
                pass
        
        # Run both directions concurrently
        await asyncio.gather(
            forward_to_eleven(),
            forward_from_eleven(),
            return_exceptions=True
        )
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    
    finally:
        # Clean up
        if eleven_ws:
            await eleven_ws.close()
        
        # End session and save data
        result = manager.end_session()
        unregister_session(session_id)
        
        # Send final summary to frontend
        try:
            await websocket.send_json({
                "type": "session_ended",
                "session_id": session_id,
                "audio_path": result["audio_path"],
                "json_path": result["json_path"],
                "message_count": len(manager.session.messages)
            })
        except:
            pass


@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation data by session ID"""
    json_path = CONVERSATIONS_DIR / f"{session_id}.json"
    
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    with open(json_path) as f:
        return json.load(f)


@app.get("/api/conversation/{session_id}/audio")
async def get_conversation_audio(session_id: str):
    """Get audio recording for a conversation"""
    audio_path = RECORDINGS_DIR / f"{session_id}.wav"
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"{session_id}.wav"
    )


@app.get("/api/conversations")
async def list_conversations():
    """List all saved conversations"""
    conversations = []
    
    for json_file in CONVERSATIONS_DIR.glob("*.json"):
        with open(json_file) as f:
            data = json.load(f)
            conversations.append({
                "session_id": data.get("session_id"),
                "started_at": data.get("started_at"),
                "ended_at": data.get("ended_at"),
                "message_count": len(data.get("messages", [])),
                "status": data.get("status")
            })
    
    # Sort by started_at descending
    conversations.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {"conversations": conversations}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

