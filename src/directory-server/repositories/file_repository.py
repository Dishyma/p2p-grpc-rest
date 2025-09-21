from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid
from ..models.peer_file import PeerFileModel
from ..models.peer import PeerModel
from ..interfaces.peer_file_repository import IPeerFileRepository
from ..contextdb.connection import db_connection

class PeerFileRepository(IPeerFileRepository):
    
    def __init__(self, session: Session = None):
        self.session = session
    
    def create(self, peer_file: PeerFileModel) -> PeerFileModel:
        if self.session:
            session = self.session
            session.add(peer_file)
            session.flush()
            session.refresh(peer_file)
        else:
            with db_connection.get_session() as session:
                session.add(peer_file)
                session.flush()
                session.refresh(peer_file)
        return peer_file
    
    def get_by_id(self, file_id: uuid.UUID) -> Optional[PeerFileModel]:
        if self.session:
            return self.session.query(PeerFileModel).filter(PeerFileModel.id == file_id).first()
        else:
            with db_connection.get_session() as session:
                return session.query(PeerFileModel).filter(PeerFileModel.id == file_id).first()
    
    def get_by_peer_id(self, peer_id: uuid.UUID) -> List[PeerFileModel]:
        if self.session:
            return self.session.query(PeerFileModel).filter(PeerFileModel.peer_id == peer_id).all()
        else:
            with db_connection.get_session() as session:
                return session.query(PeerFileModel).filter(PeerFileModel.peer_id == peer_id).all()
    
    def search_by_filename(self, filename: str) -> List[PeerFileModel]:
        if self.session:
            return self.session.query(PeerFileModel).filter(PeerFileModel.filename.ilike(f"%{filename}%")).all()
        else:
            with db_connection.get_session() as session:
                return session.query(PeerFileModel).filter(PeerFileModel.filename.ilike(f"%{filename}%")).all()
    
    def update(self, peer_file: PeerFileModel) -> PeerFileModel:
        if self.session:
            session = self.session
            session.merge(peer_file)
            session.flush()
            session.refresh(peer_file)
        else:
            with db_connection.get_session() as session:
                session.merge(peer_file)
                session.flush()
                session.refresh(peer_file)
        return peer_file
    
    def delete(self, file_id: uuid.UUID) -> bool:
        if self.session:
            result = self.session.query(PeerFileModel).filter(PeerFileModel.id == file_id).delete()
            return result > 0
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerFileModel).filter(PeerFileModel.id == file_id).delete()
                return result > 0
    
    def delete_by_peer_id(self, peer_id: uuid.UUID) -> bool:
        if self.session:
            result = self.session.query(PeerFileModel).filter(PeerFileModel.peer_id == peer_id).delete()
            return result > 0
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerFileModel).filter(PeerFileModel.peer_id == peer_id).delete()
                return result > 0
    
    def get_by_peer_and_filename(self, peer_id: uuid.UUID, filename: str) -> Optional[PeerFileModel]:
        """Buscar un archivo específico de un peer específico"""
        if self.session:
            return self.session.query(PeerFileModel).filter(
                and_(PeerFileModel.peer_id == peer_id, PeerFileModel.filename == filename)
            ).first()
        else:
            with db_connection.get_session() as session:
                return session.query(PeerFileModel).filter(
                    and_(PeerFileModel.peer_id == peer_id, PeerFileModel.filename == filename)
                ).first()
    
    def update_by_id(self, file_id: uuid.UUID, update_data: dict) -> Optional[PeerFileModel]:
        """Actualizar un archivo por ID con datos específicos"""
        if self.session:
            session = self.session
            result = session.query(PeerFileModel).filter(PeerFileModel.id == file_id).update(update_data)
            if result > 0:
                session.flush()
                return self.get_by_id(file_id)
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerFileModel).filter(PeerFileModel.id == file_id).update(update_data)
                if result > 0:
                    session.flush()
                    return session.query(PeerFileModel).filter(PeerFileModel.id == file_id).first()
        return None
