from fastapi import APIRouter, Depends
from datetime import datetime
from ....services.directory_service import DirectoryService
from ....api.dependencies import get_directory_service
from ....api.v1.schemas import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check(
    service: DirectoryService = Depends(get_directory_service)
):
    """Health check endpoint"""
    try:
        active_peers = await service.get_active_peers()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            database_status="connected",
            active_peers=len(active_peers)
        )
    except Exception:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database_status="error",
            active_peers=0
        )
