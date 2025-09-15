from typing import List, Optional
from datetime import datetime
from ..repositories.peer_repository import PeerRepository
from ..repositories.file_repository import FileRepository
from ...shared.domain.models import Peer, FileInfo, PeerStatus
from ...shared.exceptions import PeerNotFoundError, FileNotFoundError
from ...shared.loggin import get_logger

logger = get_logger(__name__)

class DirectoryService:
    """Service para lógica de negocio del directorio"""
    
    def __init__(self, peer_repo: PeerRepository, file_repo: FileRepository):
        self.peer_repo = peer_repo
        self.file_repo = file_repo
    
    async def register_peer(self, peer_id: str, ip_address: str, grpc_port: int, files: List[str]) -> Peer:
        """Registrar peer y sus archivos"""
        logger.info("Registering peer", peer_id=peer_id, ip=ip_address, port=grpc_port, file_count=len(files))
        
        # 1. Verificar si el peer ya existe
        existing_peer = await self.peer_repo.get_by_id(peer_id)
        
        if existing_peer:
            # Actualizar peer existente
            existing_peer.ip_address = ip_address
            existing_peer.grpc_port = grpc_port
            existing_peer.last_heartbeat = datetime.utcnow()
            existing_peer.status = PeerStatus.ACTIVE
            
            peer = await self.peer_repo.update(existing_peer)
        else:
            # Crear nuevo peer
            peer = Peer(
                id=peer_id,
                ip_address=ip_address,
                grpc_port=grpc_port,
                status=PeerStatus.ACTIVE,
                last_heartbeat=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            peer = await self.peer_repo.create(peer)
        
        # 2. Anunciar archivos
        if files:
            await self.announce_files(peer_id, files)
        
        logger.info("Peer registered successfully", peer_id=peer_id)
        return peer
    
    async def unregister_peer(self, peer_id: str) -> bool:
        """Desregistrar peer"""
        logger.info("Unregistering peer", peer_id=peer_id)
        
        # Eliminar archivos del peer
        await self.file_repo.remove_files_for_peer(peer_id)
        
        # Eliminar peer
        result = await self.peer_repo.delete(peer_id)
        
        if result:
            logger.info("Peer unregistered successfully", peer_id=peer_id)
        else:
            logger.warning("Peer not found for unregistration", peer_id=peer_id)
        
        return result
    
    async def search_files(self, filename: str) -> List[Peer]:
        """Buscar peers que tienen un archivo específico"""
        logger.info("Searching for file", filename=filename)
        
        peers = await self.file_repo.find_peers_with_file(filename)
        
        logger.info("File search completed", filename=filename, peers_found=len(peers))
        return peers
    
    async def announce_files(self, peer_id: str, filenames: List[str]) -> None:
        """Peer anuncia que tiene ciertos archivos"""
        logger.info("Announcing files", peer_id=peer_id, file_count=len(filenames))
        
        # Verificar que el peer existe
        peer = await self.peer_repo.get_by_id(peer_id)
        if not peer:
            raise PeerNotFoundError(f"Peer {peer_id} not found")
        
        # Anunciar cada archivo
        for filename in filenames:
            await self.file_repo.announce_file(peer_id, filename)
        
        logger.info("Files announced successfully", peer_id=peer_id)
    
    async def heartbeat(self, peer_id: str) -> bool:
        """Procesar heartbeat de peer"""
        logger.debug("Processing heartbeat", peer_id=peer_id)
        
        result = await self.peer_repo.update_heartbeat(peer_id)
        
        if not result:
            logger.warning("Heartbeat failed - peer not found", peer_id=peer_id)
        
        return result
    
    async def get_active_peers(self) -> List[Peer]:
        """Obtener todos los peers activos"""
        return await self.peer_repo.get_active_peers()
