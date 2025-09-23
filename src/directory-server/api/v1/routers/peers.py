from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.exc import IntegrityError
from typing import List
import uuid
import logging
from ....services.directory_service import DirectoryService
from ...dependencies import get_directory_service, get_current_active_user, get_auth_service
from ..schemas import (
    PeerRegisterRequest, PeerResponse, FileSearchResponse,
    HeartbeatRequest, FileAnnounceRequest, TokenData, SuccessMessage
)
from ....services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["peers"])

@router.post("/peers/register")
def register_peer(
    request: PeerRegisterRequest,
    service: DirectoryService = Depends(get_directory_service),
    auth_service: AuthService = Depends(get_auth_service),
    client_request: Request = None
):
    """
    Registrar un nuevo peer en la red P2P
    
    Este endpoint:
    1. Crea/actualiza el peer con sus credenciales en la base de datos
    2. Genera un UUID único para el peer_id
    3. Devuelve un token JWT para autenticación en futuras llamadas
    
    No requiere autenticación previa (es el punto de entrada al sistema)
    """
    try:
        logger.info(f"Solicitud de registro con auth recibida: peer_name={request.peer_name}")

        provided_ip = request.ip_address
        detected_ip = client_request.client.host if client_request else None
        client_ip = provided_ip or detected_ip
        logger.info(f"IP para registro resuelta: provided={provided_ip}, detected={detected_ip}, used={client_ip}")

        peer = service.register_peer(
            peer_name=request.peer_name,
            password=request.password,
            ip_address=client_ip,
            grpc_port=request.grpc_port
        )

        peer_data = {
            "peer_name": peer.peer_name,
            "peer_id": str(peer.id),
            "role": "peer"
        }
        access_token = auth_service.create_token(peer_data)

        logger.info(f"Peer registrado exitosamente: {peer.id}")
        return {
            "peer_id": peer.id,
            "peer_name": peer.peer_name,
            "ip_address": str(peer.ip_address),
            "grpc_port": peer.grpc_port,
            "is_active": peer.is_active,
            "last_heartbeat": peer.last_heartbeat,
            "access_token": access_token,
            "token_type": "bearer"
        }
    except IntegrityError:
        logger.warning(f"Intento de registrar peer con nombre duplicado: {request.peer_name}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Peer name '{request.peer_name}' already exists."
        )
    except Exception as e:
        logger.error(f"Error registrando peer con auth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register peer: {str(e)}"
        )

@router.post("/peers/logout", response_model=SuccessMessage)
def logout_peer(
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Marca al peer actual como inactivo (logout voluntario)."""
    try:
        peer_id_from_token = uuid.UUID(current_user.peer_id)
        
        logger.info(f"Solicitud de logout recibida para el peer: {peer_id_from_token}")
        
        success = service.logout_peer(peer_id_from_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peer no encontrado o ya inactivo."
            )
            
        return SuccessMessage(message="Logout exitoso. El peer ha sido marcado como inactivo.")
    except Exception as e:
        logger.error(f"Error durante el logout del peer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno durante el logout: {str(e)}"
        )


@router.delete("/peers/{peer_id}")
def unregister_peer(
    peer_id: uuid.UUID,
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
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
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Busca un archivo en la red"""
    try:
        files = service.search_files(filename)
        
        return {
            "filename": filename,
            "files": [
                {
                    "id": str(file.peer_id),
                    "ip_address": str(file.peer.ip_address) if getattr(file, 'peer', None) else None,
                    "grpc_port": file.peer.grpc_port if getattr(file, 'peer', None) else None,
                    "filename": file.filename,
                    "file_size": file.file_size,
                    "file_hash": file.file_hash,
                    "announced_at": file.announced_at,
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
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
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

@router.get("/peers/{peer_id}/files")
def get_peer_files(
    peer_id: str,
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Obtener archivos de un peer específico"""
    try:
        peer_uuid = uuid.UUID(peer_id)
        files = service.get_peer_files(peer_uuid)
        
        return {
            "peer_id": peer_id,
            "files": [
                {
                    "filename": file.filename,
                    "file_size": file.file_size,
                    "file_hash": file.file_hash,
                    "announced_at": file.announced_at,
                }
                for file in files
            ],
            "total_files": len(files)
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid peer ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get peer files: {str(e)}"
        )

@router.delete("/peers/{peer_id}/files/{filename}")
def remove_peer_file(
    peer_id: str,
    filename: str,
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
):
    """Eliminar un archivo específico del registro de un peer"""
    try:
        peer_uuid = uuid.UUID(peer_id)
        success = service.remove_peer_file(peer_uuid, filename)
        
        if success:
            return {"message": f"File '{filename}' removed from peer {peer_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found for peer {peer_id}"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid peer ID format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove file: {str(e)}"
        )

@router.post("/peers/heartbeat")
def heartbeat(
    request: HeartbeatRequest,
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
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
    service: DirectoryService = Depends(get_directory_service),
    current_user: TokenData = Depends(get_current_active_user)
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

