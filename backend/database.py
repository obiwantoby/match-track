import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError(
        "MONGO_URL environment variable is required. "
        "Example: mongodb://localhost:27017"
    )

DB_NAME = os.environ.get("DB_NAME", "shooting_matches_db")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def connect_to_mongo():
    """Optional hook for startup; client is created at import time."""
    pass


async def close_mongo_connection():
    client.close()
