import os
from datetime import datetime, timezone

import jwt

# Key prefix for blacklisted tokens
BLACKLIST_KEY_PREFIX = "token:blacklist:"


class TokenManager:
    """
    Manages token operations like blacklisting and validation.
    Uses cache storage for storing blacklisted tokens.
    """

    def __init__(self, cache_storage):
        """
        Initialize the token manager with a cache storage instance.
        """
        self.cache_storage = cache_storage

    async def blacklist_token(self, token: str) -> bool:
        """
        Add a token to the blacklist in cache storage.
        Returns True if successful, False otherwise.
        """
        try:
            # Decode token to get expiration time
            payload = jwt.decode(
                token,
                os.getenv("AUTH_JWT_SECRET"),
                algorithms=[os.getenv("AUTH_ALGORITHM", "HS256")],
            )
            # Get expiration time from payload
            exp_timestamp = payload.get("exp", 0)

            if exp_timestamp:
                # Calculate TTL in seconds (time until token expires)
                now = datetime.now(timezone.utc).timestamp()
                ttl = max(int(exp_timestamp - now), 0)

                # Store token in blacklist with TTL to auto-cleanup expired tokens
                key = f"{BLACKLIST_KEY_PREFIX}{token}"
                await self.cache_storage.set(key, "1", ex=ttl)
                return True
            return False
        except Exception:
            return False

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is in the blacklist.
        """
        key = f"{BLACKLIST_KEY_PREFIX}{token}"
        return await self.cache_storage.exists(key) == 1

