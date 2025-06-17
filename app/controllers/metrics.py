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
            response_model=dict[str, object],)
async def get_metrics(user: AuthenticatedUser, metrics_service: Depends(get_metrics_service)):
    return await metrics_service.get_metrics()