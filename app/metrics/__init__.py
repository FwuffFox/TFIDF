import time

from app.valkey import valkey_instance as valkey


async def process_metrics(time_taken: float):
    files_processed = await valkey.get("files_processed") or 0
    await valkey.set("files_processed", files_processed + 1)

    min_time = await valkey.get("min_processing_time") or float("inf")
    if time_taken < min_time:
        await valkey.set("min_processing_time", time_taken)

    max_time = await valkey.get("max_processing_time") or 0
    if time_taken > max_time:
        await valkey.set("max_processing_time", time_taken)

    await valkey.set(
        "average_processing_time",
        (await valkey.get("average_processing_time") or 0)
        + time_taken / (files_processed + 1),
    )

    await valkey.set("last_processing_time", time_taken)

    await valkey.set(
        "latest_file_processed_timestamp",
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    )
