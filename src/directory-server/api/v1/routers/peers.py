from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from ....services.directory_service import DirectoryService
from ....api.dependencies import get_directory_service
from ....api.v1.schemas import (
    PeerRegisterRequest, PeerResponse, FileSearchResponse,
    HeartbeatRequest, FileAnnounceRequest, HealthResponse
)
from ....shared.exceptions import PeerNotFoundError
from ....shared.loggin import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["peers"])

@router.post("/peers/register", response_model=PeerResponse)
async def register_peer(
    request: PeerRegisterRequest,
    service: DirectoryService = Depends(get_directory_service)
):
    """Registra un nuevo peer en la red"""
    try:
        peer = await service.register_peer(
            request.peer_id,
            request.ip_address,
            request.grpc_port,
            request.files
        )
        
        return PeerResponse(
            peer_id=peer.id,
            ip_address=peer.ip_address,
            grpc_port=peer.grpc_port,
            is_active=peer.status.value == "active",
            last_heartbeat=peer.last_heartbeat
        )
    except Exception as e:
        logger.error("Failed to register peer", error=str(e), peer_id=request.peer_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register peer"
        )

@router.delete("/peers/{peer_id}")
async def unregister_peer(
    peer_id: str,
    service: DirectoryService = Depends(get_directory_service)
):
    """Desregistra un peer de la red"""
    try:
        result = await service.unregister_peer(peer_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peer not found"
            )
        return {"message": "Peer unregistered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to unregister peer", error=str(e), peer_id=peer_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister peer"
        )

@router.get("/files/search", response_model=FileSearchResponse)
async def search_file(
    filename: str,
    service: DirectoryService = Depends(get_directory_service)
):
    """Busca un archivo en la red"""
    try:
        peers = await service.search_files(filename)
        
        peer_responses = [
            PeerResponse(
                peer_id=peer.id,
                ip_address=peer.ip_address,
                grpc_port=peer.grpc_port,
                is_active=peer.status.value == "active",
                last_heartbeat=peer.last_heartbeat
            )
            for peer in peers
        ]
        
        return FileSearchResponse(
            filename=filename,
            peers=peer_responses,
            total_peers=len(peer_responses)
        )
    except Exception as e:
        logger.error("Failed to search file", error=str(e), filename=filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search file"
        )

@router.post("/files/announce")
async def announce_files(
    request: FileAnnounceRequest,
    service: DirectoryService = Depends(get_directory_service)
):
    """Anuncia archivos de un peer"""
    try:
        await service.announce_files(request.peer_id, request.files)
        return {"message": "Files announced successfully"}
    except PeerNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Peer not found"
        )
    except Exception as e:
        logger.error("Failed to announce files", error=str(e), peer_id=request.peer_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to announce files"
        )

@router.post("/peers/heartbeat")
async def heartbeat(
    request: HeartbeatRequest,
    service: DirectoryService = Depends(get_directory_service)
):
    """Procesa heartbeat de un peer"""
    try:
        result = await service.heartbeat(request.peer_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peer not found"
            )
        return {"message": "Heartbeat processed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process heartbeat", error=str(e), peer_id=request.peer_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process heartbeat"
        )

@router.get("/peers", response_model=List[PeerResponse])
async def get_active_peers(
    service: DirectoryService = Depends(get_directory_service)
):
    """Obtiene todos los peers activos"""
    try:
        peers = await service.get_active_peers()
        
        return [
            PeerResponse(
                peer_id=peer.id,
                ip_address=peer.ip_address,
                grpc_port=peer.grpc_port,
                is_active=peer.status.value == "active",
                last_heartbeat=peer.last_heartbeat
            )
            for peer in peers
        ]
    except Exception as e:
        logger.error("Failed to get active peers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active peers"
        )
