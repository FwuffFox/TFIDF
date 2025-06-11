from unittest.mock import AsyncMock


class MockRedisClient:
    """A mock Redis client for testing that implements the needed methods"""

    def __init__(self, data):
        self.data = data

    async def exists(self, key):
        """Mock implementation of Redis exists method"""
        return 1 if key in self.data else 0

    async def get(self, key):
        """Mock implementation of Redis get method"""
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        """Mock implementation of Redis set method"""
        self.data[key] = value
        return True

    async def close(self):
        """Mock implementation of close method"""
        pass
