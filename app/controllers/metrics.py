from fastapi import APIRouter
from fastapi.params import Depends

from app.controllers.utils.responses import response401
from app.dependencies import get_metrics_service
from app.utils.auth import AuthenticatedUser

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    responses={401: response401},)

@router.get("/",
            summary="Get Metrics",
            description="Retrieve application metrics such as request counts, error rates, and performance statistics.",
            responses={
                200: {
                    "description": "Metrics retrieved successfully",
                    "content": {"application/json": {"example": {"request_count": 100, "error_rate": 0.05}}},
                },
            })
async def get_metrics(user: AuthenticatedUser, metrics_service: Depends(get_metrics_service)):
    return await metrics_service.get_metrics()