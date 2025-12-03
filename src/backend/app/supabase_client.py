"""
Supabase client for database and storage operations
"""
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

# Use service key for backend operations
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def save_user_profile(user_id: str, profile_data: dict) -> dict:
    """Save or update user profile (age, about_me, looking_for)"""
    data = {"user_id": user_id, **profile_data}
    
    try:
        result = supabase.table("profiles").upsert(data, on_conflict="user_id").execute()
        print(f"✅ Profile saved: {result.data}")
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        raise


async def get_user_profile(user_id: str) -> dict:
    """Get user profile"""
    result = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()
    return result.data
