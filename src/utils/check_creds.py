"""
Quick script to verify Supabase and Eleven Labs credentials
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_supabase():
    """Test Supabase connection"""
    print("\n🔍 Checking Supabase credentials...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url:
        print("❌ SUPABASE_URL not found in .env")
        return False
    if not supabase_key:
        print("❌ SUPABASE_KEY/SUPABASE_ANON_KEY not found in .env")
        return False
    
    print(f"   URL: {supabase_url[:50]}...")
    print(f"   Key: {supabase_key[:20]}...")
    
    try:
        import requests
        # Just check if we can reach the Supabase REST API with valid auth
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        }
        response = requests.get(f"{supabase_url}/rest/v1/", headers=headers)
        
        if response.status_code == 200:
            print("✅ Supabase credentials are valid!")
            return True
        elif response.status_code == 401:
            print("❌ Supabase API key is invalid (401 Unauthorized)")
            return False
        else:
            print(f"✅ Supabase connection works! (status: {response.status_code})")
            return True
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return False

def check_eleven_labs():
    """Test Eleven Labs API key"""
    print("\n🔍 Checking Eleven Labs credentials...")
    
    api_key = os.getenv("ELEVEN_LABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        print("❌ ELEVEN_LABS_API_KEY/ELEVENLABS_API_KEY not found in .env")
        return False
    
    print(f"   Key: {api_key[:15]}...")
    
    try:
        import requests
        headers = {"xi-api-key": api_key}
        response = requests.get("https://api.elevenlabs.io/v1/user", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Eleven Labs credentials valid!")
            print(f"   Subscription: {user_data.get('subscription', {}).get('tier', 'Unknown')}")
            print(f"   Character quota: {user_data.get('subscription', {}).get('character_count', 'N/A')}/{user_data.get('subscription', {}).get('character_limit', 'N/A')}")
            return True
        elif response.status_code == 401:
            print("❌ Eleven Labs API key is invalid (401 Unauthorized)")
            return False
        else:
            print(f"❌ Eleven Labs API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Eleven Labs error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔐 Credential Verification Script")
    print("=" * 50)
    
    supabase_ok = check_supabase()
    eleven_ok = check_eleven_labs()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    print(f"   Supabase: {'✅ OK' if supabase_ok else '❌ FAILED'}")
    print(f"   Eleven Labs: {'✅ OK' if eleven_ok else '❌ FAILED'}")
    print("=" * 50)

