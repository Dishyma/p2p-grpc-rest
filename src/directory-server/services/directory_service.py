from typing import List, Optional
from datetime import datetime
import uuid
from ..repositories.peer_repository import PeerRepository
from ..repositories.file_repository import PeerFileRepository
from ..models.peer import PeerModel
from ..models.peer_file import PeerFileModel

class DirectoryService:
    """Service para lógica de negocio del directorio"""
    
    def __init__(self, peer_repo: PeerRepository, file_repo: PeerFileRepository):
        self.peer_repo = peer_repo
        self.file_repo = file_repo
    
    def register_peer(self, ip_address: str, grpc_port: int, files: List[str]) -> PeerModel:
        """Registrar peer y sus archivos"""
        # Create new peer
        peer = PeerModel(
            ip_address=ip_address,
            grpc_port=grpc_port,
            is_active=True
        )
        
        created_peer = self.peer_repo.create(peer)
        
        # Announce files if provided
        if files:
            self.announce_files(created_peer.id, files)
        
        return created_peer
    
    def unregister_peer(self, peer_id: uuid.UUID) -> bool:
        """Desregistrar peer"""
        # Eliminar archivos del peer
        self.file_repo.delete_by_peer_id(peer_id)
        
        # Eliminar peer
        return self.peer_repo.delete(peer_id)
    
    def search_files(self, filename: str) -> List[PeerFileModel]:
        """Buscar archivos por nombre"""
        return self.file_repo.search_by_filename(filename)
    
    def announce_files(self, peer_id: uuid.UUID, filenames: List[str]) -> None:
        """Peer anuncia que tiene ciertos archivos"""
        # Verificar que el peer existe
        peer = self.peer_repo.get_by_id(peer_id)
        if not peer:
            raise ValueError(f"Peer {peer_id} not found")
        
        # Anunciar cada archivo
        for filename in filenames:
            peer_file = PeerFileModel(
                peer_id=peer_id,
                filename=filename
            )
            self.file_repo.create(peer_file)
    
    def heartbeat(self, peer_id: uuid.UUID) -> bool:
        """Procesar heartbeat de peer"""
        return self.peer_repo.update_heartbeat(peer_id)
    
    def get_active_peers(self) -> List[PeerModel]:
        """Obtener todos los peers activos"""
        return self.peer_repo.get_all_active()
    
    
    def get_peer_files(self, peer_id: uuid.UUID) -> List[PeerFileModel]:
        """Obtener archivos de un peer"""
        return self.file_repo.get_by_peer_id(peer_id)
