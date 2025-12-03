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

from app.config import ELEVEN_LABS_API_KEY, ELEVENLABS_AGENT_ID, CONVERSATIONS_DIR, RECORDINGS_DIR
from app.models import StartConversationRequest, StartConversationResponse, MessageRole
from app.conversation_handler import (
    create_session,
    get_session,
    register_session,
    unregister_session,
    get_signed_url,
    ConversationManager,
)
from app.supabase_client import save_user_profile

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


@app.get("/debug/supabase")
async def debug_supabase():
    """Debug endpoint to test Supabase connection"""
    from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    from app.supabase_client import supabase
    
    results = {
        "supabase_url": SUPABASE_URL[:50] + "..." if SUPABASE_URL else None,
        "service_key_set": bool(SUPABASE_SERVICE_KEY),
        "service_key_preview": SUPABASE_SERVICE_KEY[:20] + "..." if SUPABASE_SERVICE_KEY else None,
    }
    
    # Test table access
    try:
        # Try to select from profiles
        result = supabase.table("profiles").select("count").limit(1).execute()
        results["profiles_table"] = "✅ accessible"
        results["profiles_data"] = str(result.data)
    except Exception as e:
        results["profiles_table"] = f"❌ error: {str(e)}"
    
    # Test storage access
    try:
        buckets = supabase.storage.list_buckets()
        results["storage_buckets"] = [b.name for b in buckets] if buckets else []
    except Exception as e:
        results["storage_buckets"] = f"❌ error: {str(e)}"
    
    return results


@app.post("/api/conversation/start", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """Start a new conversation session"""
    
    if not ELEVEN_LABS_API_KEY or not ELEVENLABS_AGENT_ID:
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


def handle_tool_call(manager: ConversationManager, tool_name: str, tool_args: dict) -> str:
    """Handle tool calls from the agent"""
    if tool_name == "update_dating_profile":
        profile = manager.update_profile(**tool_args)
        return json.dumps({
            "success": True,
            "message": "Profile updated",
            "current_profile": profile.model_dump() if profile else {}
        })
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def finalize_session(manager: ConversationManager):
    """
    Finalize the session:
    1. Save profile to Supabase (age, about_me, looking_for)
    """
    user_id = manager.user_id
    if not user_id:
        print("⚠️ No user_id, skipping Supabase save")
        return
    
    profile = manager.session.profile
    print(f"📋 Final profile data: {profile.model_dump() if profile else 'None'}")
    
    # Save profile to Supabase
    if profile:
        try:
            profile_data = {
                "age": profile.age,
                "about_me": profile.about_me,
                "looking_for": profile.looking_for,
                "profile_completed": True,
            }
            # Remove None values
            profile_data = {k: v for k, v in profile_data.items() if v is not None}
            
            print(f"💾 Saving to Supabase: {profile_data}")
            await save_user_profile(user_id, profile_data)
            print(f"✅ Profile saved to Supabase for user {user_id}")
        except Exception as e:
            print(f"❌ Failed to save profile: {e}")
    else:
        print("⚠️ No profile data to save")


@app.websocket("/api/conversation/{session_id}/ws")
async def conversation_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint that bridges the frontend to Eleven Labs Conversational AI
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
        
        print(f"🔗 Got signed URL, connecting to Eleven Labs...")
        
        if not signed_url:
            await websocket.send_json({"type": "error", "message": "Failed to get Eleven Labs URL"})
            return
        
        # Connect to Eleven Labs
        eleven_ws = await websockets.connect(signed_url)
        print(f"✅ Connected to Eleven Labs")
        
        # Ready will be sent when we receive conversation_initiation_metadata from Eleven Labs
        print("⏳ Waiting for Eleven Labs to initialize...")
        
        async def forward_to_eleven():
            """Forward messages from frontend to Eleven Labs"""
            audio_count = 0
            try:
                while True:
                    data = await websocket.receive()
                    
                    if "text" in data:
                        try:
                            msg = json.loads(data["text"])
                            print(f"📤 From frontend (text): {msg.get('type', 'unknown')}")
                            
                            if msg.get("type") == "end_conversation":
                                print("🛑 User ended conversation")
                                break
                            
                            await eleven_ws.send(data["text"])
                        except json.JSONDecodeError:
                            print(f"📤 From frontend (non-json text): {data['text'][:50]}")
                        
                    elif "bytes" in data:
                        audio_bytes = data["bytes"]
                        audio_count += 1
                        if audio_count % 50 == 1:  # Log every 50th chunk
                            print(f"🎤 Audio chunk #{audio_count}: {len(audio_bytes)} bytes")
                        manager.add_audio_chunk(audio_bytes)
                        
                        # Eleven Labs expects base64 audio in JSON format
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                        audio_message = {
                            "user_audio_chunk": audio_base64
                        }
                        await eleven_ws.send(json.dumps(audio_message))
                    
                    elif "type" in data and data["type"] == "websocket.disconnect":
                        print(f"📴 Frontend WebSocket disconnect event")
                        break
                        
            except WebSocketDisconnect as e:
                print(f"📴 Frontend disconnected (WebSocketDisconnect). Total audio chunks: {audio_count}")
            except Exception as e:
                print(f"❌ forward_to_eleven error: {e}")
                import traceback
                traceback.print_exc()
        
        async def forward_from_eleven():
            """Forward messages from Eleven Labs to frontend"""
            message_count = 0
            audio_count = 0
            try:
                async for message in eleven_ws:
                    message_count += 1
                    
                    if isinstance(message, str):
                        msg_data = json.loads(message)
                        msg_type = msg_data.get("type")
                        
                        # Log non-ping messages
                        if msg_type != "ping":
                            print(f"📨 From Eleven Labs ({msg_type}): {message[:150]}...")
                        
                        # Handle audio events - decode base64 and send as binary
                        if "audio_event" in msg_data:
                            audio_base64 = msg_data["audio_event"].get("audio_base_64")
                            if audio_base64:
                                audio_count += 1
                                audio_bytes = base64.b64decode(audio_base64)
                                if audio_count % 10 == 1:
                                    print(f"🔊 Sending audio #{audio_count} to frontend: {len(audio_bytes)} bytes")
                                await websocket.send_bytes(audio_bytes)
                        
                        # Handle user transcript
                        elif msg_type == "user_transcript":
                            event_data = msg_data.get("user_transcription_event", {})
                            text = event_data.get("user_transcript", "")
                            if text:
                                manager.add_message(MessageRole.USER, text)
                                await websocket.send_json({
                                    "type": "user_transcript",
                                    "user_transcript": text
                                })
                        
                        # Handle agent response
                        elif msg_type == "agent_response":
                            event_data = msg_data.get("agent_response_event", {})
                            text = event_data.get("agent_response", "")
                            if text:
                                manager.add_message(MessageRole.AGENT, text)
                                await websocket.send_json({
                                    "type": "agent_response",
                                    "agent_response": text
                                })
                        
                        # Handle tool calls (Eleven Labs sends "client_tool_call" type)
                        elif msg_type == "client_tool_call" or "client_tool_call" in msg_data:
                            tool_data = msg_data.get("client_tool_call", {})
                            tool_name = tool_data.get("tool_name")
                            tool_call_id = tool_data.get("tool_call_id")
                            tool_args = tool_data.get("parameters", {})
                            
                            print(f"🔧 Tool call: {tool_name} with args: {tool_args}")
                            
                            result = handle_tool_call(manager, tool_name, tool_args)
                            
                            # Send response back to Eleven Labs
                            tool_response = {
                                "type": "client_tool_result",
                                "tool_call_id": tool_call_id,
                                "result": json.dumps(result)
                            }
                            await eleven_ws.send(json.dumps(tool_response))
                            print(f"✅ Tool result sent: {result}")
                            
                            await websocket.send_json({
                                "type": "profile_updated",
                                "profile": manager.session.profile.model_dump() if manager.session.profile else {}
                            })
                        
                        # Handle conversation init (type is in the message)
                        if "conversation_initiation_metadata_event" in msg_data:
                            print("✅ Eleven Labs conversation initialized")
                            await websocket.send_json({
                                "type": "ready",
                                "session_id": session_id
                            })
                        
                        # Handle pings - respond with pong
                        elif msg_type == "ping":
                            ping_event = msg_data.get("ping_event", {})
                            event_id = ping_event.get("event_id")
                            pong = {"type": "pong", "event_id": event_id}
                            await eleven_ws.send(json.dumps(pong))
                        
                    else:
                        # Binary audio data (fallback)
                        audio_count += 1
                        await websocket.send_bytes(message)
                        
            except websockets.exceptions.ConnectionClosed as e:
                print(f"📴 Eleven Labs connection closed: {e.code} - {e.reason}")
            except Exception as e:
                print(f"❌ forward_from_eleven error: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"📊 Eleven Labs session ended. Messages: {message_count}, Audio chunks: {audio_count}")
        
        # Run both directions concurrently
        results = await asyncio.gather(
            forward_to_eleven(),
            forward_from_eleven(),
            return_exceptions=True
        )
        
        print(f"🔄 Gather completed. Results: {results}")
        
    except Exception as e:
        print(f"❌ Main error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    
    finally:
        print(f"🔚 Connection ending. Total audio chunks: {len(manager.audio_chunks)}")
        
        if eleven_ws:
            await eleven_ws.close()
        
        # End session and save locally
        manager.session.ended_at = datetime.utcnow()
        manager.session.status = "completed"
        
        # Save to Supabase
        await finalize_session(manager)
        
        # Also save locally as backup
        manager.save_conversation_json()
        print(f"💾 Saved conversation locally")
        
        profile_data = manager.session.profile.model_dump() if manager.session.profile else None
        
        unregister_session(session_id)
        
        try:
            await websocket.send_json({
                "type": "session_ended",
                "session_id": session_id,
                "message_count": len(manager.session.messages),
                "profile": profile_data
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
                "status": data.get("status"),
                "profile": data.get("profile")
            })
    
    conversations.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {"conversations": conversations}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
