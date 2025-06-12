import os
from datetime import datetime, timezone

import jwt

# Key prefix for blacklisted tokens
BLACKLIST_KEY_PREFIX = "token:blacklist:"
# Key prefix for user tokens
USER_TOKEN_KEY_PREFIX = "user:tokens:"


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

    async def blacklist_all_user_tokens(self, username: str) -> bool:
        """
        Blacklist all tokens for a specific user.
        This is useful when a user changes their password or is deleted.

        Returns True if successful, False otherwise.
        """
        try:
            # Create a pattern that blacklists all tokens for this user
            # This will create a key in cache that can be checked during token validation
            key = f"{USER_TOKEN_KEY_PREFIX}{username}:invalidated_before"
            # Set the current time as the invalidation timestamp
            current_time = datetime.now(timezone.utc).timestamp()
            # Store for 30 days (typical token max lifetime)
            await self.cache_storage.set(
                key, str(current_time), ex=2592000
            )  # 30 days in seconds
            return True
        except Exception:
            return False
