from fastapi import APIRouter, Depends
from datetime import datetime
from ....services.directory_service import DirectoryService
from ...dependencies import get_directory_service
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health_check(
    service: DirectoryService = Depends(get_directory_service)
):
    """Health check endpoint"""
    try:
        active_peers = service.get_active_peers()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            database_status="connected",
            active_peers=len(active_peers)
        )
    except Exception:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            database_status="error",
            active_peers=0
        )
