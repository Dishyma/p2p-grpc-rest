from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import uuid
from ..models.peer import PeerModel
from ..interfaces.peer_repository import IPeerRepository
from ..contextdb.connection import db_connection

class PeerRepository(IPeerRepository):
    
    def __init__(self, session: Session = None):
        self.session = session
    
    def create(self, peer: PeerModel) -> PeerModel:
        if self.session:
            session = self.session
            session.add(peer)
            session.flush()
            session.refresh(peer)
        else:
            with db_connection.get_session() as session:
                session.add(peer)
                session.flush()
                session.refresh(peer)
        return peer
    
    def get_by_id(self, peer_id: uuid.UUID) -> Optional[PeerModel]:
        if self.session:
            return self.session.query(PeerModel).filter(PeerModel.id == peer_id).first()
        else:
            with db_connection.get_session() as session:
                return session.query(PeerModel).filter(PeerModel.id == peer_id).first()
    
    def get_all_active(self) -> List[PeerModel]:
        if self.session:
            return self.session.query(PeerModel).filter(PeerModel.is_active == True).all()
        else:
            with db_connection.get_session() as session:
                return session.query(PeerModel).filter(PeerModel.is_active == True).all()
    
    
    def update(self, peer: PeerModel) -> PeerModel:
        if self.session:
            session = self.session
            session.merge(peer)
            session.flush()
            session.refresh(peer)
        else:
            with db_connection.get_session() as session:
                session.merge(peer)
                session.flush()
                session.refresh(peer)
        return peer
    
    def delete(self, peer_id: uuid.UUID) -> bool:
        if self.session:
            result = self.session.query(PeerModel).filter(PeerModel.id == peer_id).delete()
            return result > 0
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerModel).filter(PeerModel.id == peer_id).delete()
                return result > 0
    
    def update_heartbeat(self, peer_id: uuid.UUID) -> bool:
        if self.session:
            result = self.session.query(PeerModel).filter(
                PeerModel.id == peer_id
            ).update({
                PeerModel.last_heartbeat: datetime.utcnow(),
                PeerModel.is_active: True
            })
            return result > 0
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerModel).filter(
                    PeerModel.id == peer_id
                ).update({
                    PeerModel.last_heartbeat: datetime.utcnow(),
                    PeerModel.is_active: True
                })
                return result > 0
