from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
from ....services.directory_service import DirectoryService
from ...dependencies import get_directory_service
from ..schemas import (
    PeerRegisterRequest, PeerResponse, FileSearchResponse,
    HeartbeatRequest, FileAnnounceRequest
)

router = APIRouter(tags=["peers"])

@router.post("/peers/register", response_model=PeerResponse)
def register_peer(
    request: PeerRegisterRequest,
    service: DirectoryService = Depends(get_directory_service)
):
    """Registrar un nuevo peer en el directorio"""
    try:
        peer = service.register_peer(
            ip_address=request.ip_address,
            grpc_port=request.grpc_port,
            files=request.files
        )
        
        return PeerResponse(
            peer_id=peer.id,
            ip_address=str(peer.ip_address),
            grpc_port=peer.grpc_port,
            is_active=peer.is_active,
            last_heartbeat=peer.last_heartbeat
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register peer: {str(e)}"
        )

@router.delete("/peers/{peer_id}")
def unregister_peer(
    peer_id: uuid.UUID,
    service: DirectoryService = Depends(get_directory_service)
):
    """Desregistra un peer de la red"""
    try:
        result = service.unregister_peer(peer_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peer not found"
            )
        return {"message": "Peer unregistered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister peer: {str(e)}"
        )

@router.get("/peers/files/search")
def search_file(
    filename: str,
    service: DirectoryService = Depends(get_directory_service)
):
    """Busca un archivo en la red"""
    try:
        files = service.search_files(filename)
        
        return {
            "filename": filename,
            "files": [
                {
                    "id": str(file.id),
                    "filename": file.filename,
                    "peer_id": str(file.peer_id),
                    "file_size": file.file_size,
                    "file_hash": file.file_hash,
                    "announced_at": file.announced_at
                }
                for file in files
            ],
            "total_files": len(files)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search file: {str(e)}"
        )

@router.post("/peers/files/announce")
def announce_files(
    request: FileAnnounceRequest,
    service: DirectoryService = Depends(get_directory_service)
):
    """Anuncia archivos de un peer"""
    try:
        service.announce_files(request.peer_id, request.files)
        return {"message": "Files announced successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to announce files: {str(e)}"
        )

@router.post("/peers/heartbeat")
def heartbeat(
    request: HeartbeatRequest,
    service: DirectoryService = Depends(get_directory_service)
):
    """Procesa heartbeat de un peer"""
    try:
        result = service.heartbeat(request.peer_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peer not found"
            )
        return {"message": "Heartbeat processed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process heartbeat: {str(e)}"
        )

@router.get("/peers", response_model=List[PeerResponse])
def get_active_peers(
    service: DirectoryService = Depends(get_directory_service)
):
    """Obtiene todos los peers activos"""
    try:
        peers = service.get_active_peers()
        
        return [
            PeerResponse(
                peer_id=peer.id,
                ip_address=str(peer.ip_address),
                grpc_port=peer.grpc_port,
                is_active=peer.is_active,
                last_heartbeat=peer.last_heartbeat
            )
            for peer in peers
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active peers: {str(e)}"
        )

