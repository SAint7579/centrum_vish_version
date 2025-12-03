"""
Simple test script to verify the conversation API works
Run this after starting the server with `python run.py`
"""
import asyncio
import json
import httpx
import websockets


async def test_conversation():
    """Test the conversation flow"""
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Centrum Conversation API\n")
    
    # 1. Check health
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        print(f"✅ Health check: {response.json()}")
        
        # 2. Start a conversation
        response = await client.post(
            f"{base_url}/api/conversation/start",
            json={"user_id": "test-user-123"}
        )
        data = response.json()
        session_id = data["session_id"]
        ws_url = data["websocket_url"]
        print(f"✅ Started session: {session_id}")
        print(f"   WebSocket URL: {ws_url}")
    
    # 3. Connect to WebSocket (just test connection)
    print("\n📡 Testing WebSocket connection...")
    try:
        ws_full_url = f"ws://localhost:8000{ws_url}"
        async with websockets.connect(ws_full_url) as ws:
            # Wait for ready message
            message = await asyncio.wait_for(ws.recv(), timeout=10)
            msg_data = json.loads(message)
            
            if msg_data.get("type") == "ready":
                print(f"✅ WebSocket ready! Session: {msg_data.get('session_id')}")
            elif msg_data.get("type") == "error":
                print(f"❌ Error: {msg_data.get('message')}")
            else:
                print(f"📨 Received: {msg_data}")
                
            # Close gracefully
            await ws.send(json.dumps({"type": "end_conversation"}))
            
    except asyncio.TimeoutError:
        print("⏰ WebSocket connection timed out")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    
    # 4. List conversations
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/conversations")
        convos = response.json().get("conversations", [])
        print(f"\n📋 Total conversations saved: {len(convos)}")
        
    print("\n✨ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_conversation())

