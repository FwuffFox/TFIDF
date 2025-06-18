import time
import json
from valkey.asyncio import Redis


class MetricsService:
    def __init__(self, cache_storage: Redis):
        self.cache_storage = cache_storage

    async def file_processed(self, time_taken: float, times: int = 1) -> None:
        # Integer metrics
        files_processed_raw = await self.cache_storage.get("files_processed")
        files_processed = int(files_processed_raw.decode()) if files_processed_raw else 0
        files_processed += times
        await self.cache_storage.set("files_processed", str(files_processed))

        # Min processing time
        min_time_raw = await self.cache_storage.get("min_processing_time")
        min_time = float(min_time_raw.decode()) if min_time_raw else float("inf")
        if time_taken < min_time:
            await self.cache_storage.set("min_processing_time", str(time_taken))

        # Max processing time
        max_time_raw = await self.cache_storage.get("max_processing_time")
        max_time = float(max_time_raw.decode()) if max_time_raw else 0
        if time_taken > max_time:
            await self.cache_storage.set("max_processing_time", str(time_taken))

        # Total processing time
        total_time_raw = await self.cache_storage.get("total_processing_time")
        total_time = float(total_time_raw.decode()) if total_time_raw else 0
        total_time += time_taken
        await self.cache_storage.set("total_processing_time", str(total_time))

        # Average time
        average_time = total_time / files_processed if files_processed > 0 else 0
        await self.cache_storage.set("average_processing_time", str(average_time))

        # Last processing time
        await self.cache_storage.set("last_processing_time", str(time_taken))

        # Latest timestamp (human-readable)
        current_time = time.time()
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
        await self.cache_storage.set("latest_file_processed_timestamp", timestamp_str)

        # Track timestamps (in list, stored as JSON)
        history_raw = await self.cache_storage.get("processing_timestamps")
        if history_raw:
            try:
                processing_history = json.loads(history_raw)
            except json.JSONDecodeError:
                processing_history = []
        else:
            processing_history = []

        processing_history.append(current_time)

        # Keep only entries from last 24h
        one_day_ago = current_time - 86400
        processing_history = [ts for ts in processing_history if ts > one_day_ago]

        await self.cache_storage.set("processing_timestamps", json.dumps(processing_history))

    async def get_metrics(self) -> dict:
        def decode_float(value):
            return float(value.decode()) if value else 0

        def decode_str(value):
            return value.decode() if value else "N/A"

        def decode_optional_float(value):
            return float(value.decode()) if value else None

        files_processed = int((await self.cache_storage.get("files_processed") or b"0").decode())
        min_time = decode_optional_float(await self.cache_storage.get("min_processing_time"))
        max_time = decode_float(await self.cache_storage.get("max_processing_time"))
        average_time = decode_float(await self.cache_storage.get("average_processing_time"))
        last_time = decode_float(await self.cache_storage.get("last_processing_time"))
        total_time = decode_float(await self.cache_storage.get("total_processing_time"))
        latest_file_timestamp = decode_str(await self.cache_storage.get("latest_file_processed_timestamp"))

        # Load timestamp history
        history_raw = await self.cache_storage.get("processing_timestamps")
        if history_raw:
            try:
                processing_history = json.loads(history_raw)
            except json.JSONDecodeError:
                processing_history = []
        else:
            processing_history = []

        one_day_ago = time.time() - 86400
        files_last_24h = len([ts for ts in processing_history if ts > one_day_ago])

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
