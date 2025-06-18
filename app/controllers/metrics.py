from fastapi import APIRouter
from fastapi.params import Depends

from app.controllers.utils.responses import response401
from app.dependencies import get_metrics_service
from app.services.auth import AuthenticatedUser
from app.services.metrics import MetricsService

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    responses={401: response401},
)


@router.get(
    "/",
    summary="Get Metrics",
    description="Retrieve application metrics such as request counts, error rates, and performance statistics.",
    responses={
        200: {
            "description": "Metrics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "files_processed": 100,
                        "min_processing_time": 0.1,
                        "max_processing_time": 2.5,
                        "average_processing_time": 0.5,
                        "last_processing_time": 0.3,
                        "latest_file_processed_timestamp": "2023-10-01 12:00:00",
                        "total_processing_time": 10.0,
                        "files_processed_last_24h": 50,
                    }
                }
            },
        },
    },
)
async def get_metrics(
    user: AuthenticatedUser,
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    return await metrics_service.get_metrics()
