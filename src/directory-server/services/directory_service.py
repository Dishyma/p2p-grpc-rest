from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid
import hashlib
import logging
from ..repositories.peer_repository import PeerRepository
from ..repositories.file_repository import PeerFileRepository
from ..models.peer import PeerModel
from ..models.peer_file import PeerFileModel

logger = logging.getLogger(__name__)

class DirectoryService:
    """Service para lógica de negocio del directorio"""
    
    def __init__(self, peer_repo: PeerRepository, file_repo: PeerFileRepository):
        self.peer_repo = peer_repo
        self.file_repo = file_repo
    
    def _hash_password(self, password: str) -> str:
        """Hash simple de contraseña usando SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_peer(self, peer_name: str, password: str, ip_address: str, grpc_port: int) -> PeerModel:
        """Registra o actualiza un peer con credenciales."""
        # Buscar peer existente por nombre
        peer = self.peer_repo.get_by_name(peer_name)
        password_hash = self._hash_password(password)

        if peer:
            # Si el peer existe, actualizar sus datos y reactivarlo
            update_data = {
                "password_hash": password_hash,
                "ip_address": ip_address,
                "grpc_port": grpc_port,
                "is_active": True, 
                "last_heartbeat": datetime.utcnow()
            }
            updated_peer = self.peer_repo.update(peer.id, update_data)
            # Limpiar archivos viejos para forzar un re-anuncio limpio
            self.file_repo.delete_by_peer_id(peer.id)
            return updated_peer
        else:
            # Si no existe, crear un nuevo peer
            new_peer = PeerModel(
                peer_name=peer_name,
                password_hash=password_hash,
                ip_address=ip_address, 
                grpc_port=grpc_port
            )
            created_peer = self.peer_repo.create(new_peer)
            return created_peer
    
    def unregister_peer(self, peer_id: str) -> bool:
        """Desregistrar peer"""
        # Eliminar archivos del peer
        self.file_repo.delete_by_peer_id(peer_id)
        
        # Eliminar peer
        return self.peer_repo.delete(peer_id)

    def logout_peer(self, peer_id: uuid.UUID) -> bool:
        """Marca a un peer como inactivo en la base de datos."""
        peer = self.peer_repo.get_by_id(peer_id)
        if not peer:
            return False
        
        updated_peer = self.peer_repo.update(peer.id, {"is_active": False})
        return updated_peer is not None
    
    def search_files(self, filename: str) -> List[PeerFileModel]:
        """Buscar archivos por nombre"""
        return self.file_repo.search_by_filename(filename)

    def get_peer_by_id(self, peer_id: uuid.UUID) -> Optional[PeerModel]:
        """Obtener un peer por ID"""
        return self.peer_repo.get_by_id(peer_id)
    
    def announce_files(self, peer_id: str, files: List[Any]) -> None:
        """Peer anuncia que tiene ciertos archivos.
        Acepta tanto una lista de nombres (List[str]) como una lista de objetos con
        atributos/campos: filename, size, hash.
        """
        # Convertir string a UUID y verificar que el peer existe
        peer_uuid = uuid.UUID(peer_id)
        peer = self.peer_repo.get_by_id(peer_uuid)
        if not peer:
            raise ValueError(f"Peer {peer_id} not found")

        if not files:
            return

        for item in files:
            # Normalizar entrada
            if isinstance(item, str):
                filename = item
                file_size = None
                file_hash = None
            else:
                # Puede ser un pydantic model (atributos) o dict
                filename = getattr(item, 'filename', None) or (item.get('filename') if isinstance(item, dict) else None)
                file_size = getattr(item, 'size', None) or (item.get('size') if isinstance(item, dict) else None)
                file_hash = getattr(item, 'hash', None) or (item.get('hash') if isinstance(item, dict) else None)

            if not filename:
                # Si no hay filename, ignorar registro inválido
                continue

            # Intentar crear o actualizar el archivo (upsert)
            existing_file = self.file_repo.get_by_peer_and_filename(peer_uuid, filename)
            if existing_file:
                # Actualizar archivo existente con nueva información
                update_data = {}
                if file_size is not None:
                    update_data['file_size'] = file_size
                if file_hash is not None:
                    update_data['file_hash'] = file_hash
                if update_data:
                    self.file_repo.update_by_id(existing_file.id, update_data)
            else:
                # Crear nuevo archivo
                peer_file = PeerFileModel(
                    peer_id=peer_uuid,
                    filename=filename,
                    file_size=file_size,
                    file_hash=file_hash,
                )
                self.file_repo.create(peer_file)
    
    def heartbeat(self, peer_id: str) -> bool:
        """Procesar heartbeat de un peer"""
        peer_uuid = uuid.UUID(peer_id)
        return self.peer_repo.update_heartbeat(peer_uuid)
    
    def get_active_peers(self) -> List[PeerModel]:
        """Obtener todos los peers activos (con limpieza automática)"""
        # Primero limpiar peers inactivos (sin heartbeat por más de 5 minutos)
        self.cleanup_inactive_peers()
        return self.peer_repo.get_all_active()
    
    def cleanup_inactive_peers(self) -> int:
        """Limpiar peers que no han enviado heartbeat en los últimos 5 minutos"""
        from datetime import timedelta
        timeout_minutes = 5
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        # Marcar peers como inactivos si no han enviado heartbeat
        inactive_count = self.peer_repo.mark_inactive_by_timeout(cutoff_time)
        if inactive_count > 0:
            logger.info(f"[CLEANUP] Marcados {inactive_count} peers como inactivos por timeout")
        
        return inactive_count
    
    
    def get_peer_files(self, peer_id: uuid.UUID) -> List[PeerFileModel]:
        """Obtener archivos de un peer"""
        return self.file_repo.get_by_peer_id(peer_id)
    
    def remove_peer_file(self, peer_id: uuid.UUID, filename: str) -> bool:
        """Eliminar un archivo específico del registro de un peer"""
        # Buscar el archivo específico del peer
        peer_file = self.file_repo.get_by_peer_and_filename(peer_id, filename)
        if peer_file:
            return self.file_repo.delete(peer_file.id)
        return False
