
import os

from valkey.asyncio import Valkey

valkey_instance = Valkey(host=os.getenv("VALKEY_HOST", "localhost"),
                       port=int(os.getenv("VALKEY_PORT", 6379)),
                       db=int(os.getenv("VALKEY_DB", 0)))