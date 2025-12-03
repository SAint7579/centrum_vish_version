import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
CONVERSATIONS_DIR = DATA_DIR / "conversations"

# Create directories if they don't exist
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

# Eleven Labs
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "agent_4801kbjgnpzvftarm9ast510wj2q")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
