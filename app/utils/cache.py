import os

from valkey.asyncio import Redis

cache_storage = Redis(
    host=os.getenv("VALKEY_HOST", "localhost"),
    port=int(os.getenv("VALKEY_PORT", 6379)),
    db=int(os.getenv("VALKEY_DB", 0)),
)
