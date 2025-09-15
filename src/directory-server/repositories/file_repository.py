from typing import List
from sqlalchemy.orm import Session, joinedload
from ...shared.database.models import PeerFileModel, PeerModel
from ...shared.domain.models import FileInfo, Peer
from ...shared.database.connection import db_connection

class FileRepository:
    
    def __init__(self, session: Session = None):
        self.session = session
    
    async def get_files_by_peer(self, peer_id: str) -> List[FileInfo]:
        if self.session:
            session = self.session
        else:
            session = next(db_connection.get_session())
        
        try:
            files = session.query(PeerFileModel).filter(
                PeerFileModel.peer_id == peer_id
            ).all()
            
            return [self._to_domain(file) for file in files]
        finally:
            if not self.session:
                session.close()
    
    async def find_peers_with_file(self, filename: str) -> List[Peer]:
        if self.session:
            session = self.session
        else:
            session = next(db_connection.get_session())
        
        try:
            # Join para obtener peers que tienen el archivo
            results = session.query(PeerModel).join(PeerFileModel).filter(
                PeerFileModel.filename == filename,
                PeerModel.is_active == True
            ).all()
            
            return [self._peer_to_domain(peer) for peer in results]
        finally:
            if not self.session:
                session.close()
    
    async def announce_file(self, peer_id: str, filename: str, file_size: int = 0, file_hash: str = "") -> FileInfo:
        file_entity = PeerFileModel(
            peer_id=peer_id,
            filename=filename,
            file_size=file_size,
            file_hash=file_hash
        )
        
        if self.session:
            session = self.session
            # Eliminar archivo existente si ya está anunciado
            session.query(PeerFileModel).filter(
                PeerFileModel.peer_id == peer_id,
                PeerFileModel.filename == filename
            ).delete()
            
            session.add(file_entity)
            session.flush()
            session.refresh(file_entity)
        else:
            with db_connection.get_session() as session:
                # Eliminar archivo existente si ya está anunciado
                session.query(PeerFileModel).filter(
                    PeerFileModel.peer_id == peer_id,
                    PeerFileModel.filename == filename
                ).delete()
                
                session.add(file_entity)
                session.flush()
                session.refresh(file_entity)
        
        return self._to_domain(file_entity)
    
    async def remove_files_for_peer(self, peer_id: str) -> bool:
        if self.session:
            session = self.session
            result = session.query(PeerFileModel).filter(
                PeerFileModel.peer_id == peer_id
            ).delete()
            return result > 0
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerFileModel).filter(
                    PeerFileModel.peer_id == peer_id
                ).delete()
                return result > 0
    
    def _to_domain(self, file_model: PeerFileModel) -> FileInfo:
        return FileInfo(
            filename=file_model.filename,
            size=file_model.file_size or 0,
            hash=file_model.file_hash or "",
            peer_id=file_model.peer_id,
            announced_at=file_model.announced_at
        )
    
    def _peer_to_domain(self, peer_model: PeerModel) -> Peer:
        from ...shared.domain.models import PeerStatus
        return Peer(
            id=peer_model.id,
            ip_address=str(peer_model.ip_address),
            grpc_port=peer_model.grpc_port,
            status=PeerStatus.ACTIVE if peer_model.is_active else PeerStatus.INACTIVE,
            last_heartbeat=peer_model.last_heartbeat,
            created_at=peer_model.created_at
        )
