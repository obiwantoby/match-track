# filepath: backend/database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables if you have a .env file at the root of backend
# Adjust path if your .env is elsewhere relative to this file
# Or ensure MONGO_URL and DB_NAME are set in the environment before this runs
# For consistency with server.py, let's assume .env is in backend/
# ROOT_DIR = Path(__file__).parent
# load_dotenv(ROOT_DIR / ".env") # This might be redundant if server.py already loads it early enough

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "shooting_matches_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

async def connect_to_mongo():
    # You can add any connection logic here if needed, e.g., pinging the server
    # For now, client instantiation is usually enough.
    pass

async def close_mongo_connection():
    client.close()