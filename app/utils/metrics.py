import time
from datetime import datetime, timedelta

from valkey.asyncio import Redis


class MetricsService:
    def __init__(self, cache_storage: Redis):
        """
        Initialize the metrics service with a cache storage instance.
        """
        self.cache_storage = cache_storage

    async def file_processed(self, time_taken: float) -> None:
        files_processed = self.cache_storage.get("files_processed") or 0
        files_processed += 1
        await self.cache_storage.set("files_processed", files_processed)

        min_time = await self.cache_storage.get("min_processing_time") or float("inf")
        if time_taken < min_time:
            await self.cache_storage.set("min_processing_time", time_taken)

        max_time = await self.cache_storage.get("max_processing_time") or 0
        if time_taken > max_time:
            await self.cache_storage.set("max_processing_time", time_taken)

        await self.cache_storage.set(
            "average_processing_time",
            (await self.cache_storage.get("average_processing_time") or 0)
            + time_taken / (files_processed + 1),
        )

        # Update total processing time
        total_time = await self.cache_storage.get("total_processing_time") or 0
        total_time += time_taken
        await self.cache_storage.set("total_processing_time", total_time)

        await self.cache_storage.set("last_processing_time", time_taken)

        current_time = time.time()
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))

        await self.cache_storage.set(
            "latest_file_processed_timestamp",
            current_timestamp,
        )

        # Track files processed in the last 24 hours
        # Store timestamp as a list in Redis
        processing_history = await self.cache_storage.get("processing_timestamps") or []
        processing_history.append(current_time)

        # Keep only timestamps from the last 24 hours
        one_day_ago = current_time - 86400  # 24 hours in seconds
        processing_history = [ts for ts in processing_history if ts > one_day_ago]

        await self.cache_storage.set("processing_timestamps", processing_history)

    async def get_metrics(self) -> dict:
        files_processed = await self.cache_storage.get("files_processed") or 0
        min_time = await self.cache_storage.get("min_processing_time") or None
        max_time = await self.cache_storage.get("max_processing_time") or 0
        average_time = await self.cache_storage.get("average_processing_time") or 0
        last_time = await self.cache_storage.get("last_processing_time") or 0
        total_time = await self.cache_storage.get("total_processing_time") or 0
        latest_file_timestamp = (
            await self.cache_storage.get("latest_file_processed_timestamp") or "N/A"
        )

        # Calculate files processed in the last 24 hours
        processing_history = await self.cache_storage.get("processing_timestamps") or []
        one_day_ago = time.time() - 86400  # 24 hours in seconds
        files_last_24h = len([ts for ts in processing_history if ts > one_day_ago])

        # Handle infinity case for JSON serialization
        if min_time is None or min_time == float("inf"):
            min_time = None

        return {
            "files_processed": files_processed,
            "min_processing_time": min_time,
            "max_processing_time": max_time,
            "average_processing_time": average_time,
            "last_processing_time": last_time,
            "latest_file_processed_timestamp": latest_file_timestamp,
            "total_processing_time": total_time,
            "files_processed_last_24h": files_last_24h,
        }
