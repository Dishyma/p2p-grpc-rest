from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from ...shared.database.models import PeerModel
from ...shared.repositories.base import BaseRepository
from ...shared.domain.models import Peer, PeerStatus
from ...shared.database.connection import db_connection

class PeerRepository(BaseRepository[Peer]):
    
    def __init__(self, session: Session = None):
        self.session = session
    
    async def create(self, peer: Peer) -> Peer:
        db_peer = PeerModel(
            id=peer.id,
            ip_address=peer.ip_address,
            grpc_port=peer.grpc_port,
            is_active=True
        )
        
        if self.session:
            session = self.session
            session.add(db_peer)
            session.flush()
            session.refresh(db_peer)
        else:
            with db_connection.get_session() as session:
                session.add(db_peer)
                session.flush()
                session.refresh(db_peer)
        
        return self._to_domain(db_peer)
    
    async def get_by_id(self, peer_id: str) -> Optional[Peer]:
        if self.session:
            db_peer = self.session.query(PeerModel).filter(PeerModel.id == peer_id).first()
        else:
            with db_connection.get_session() as session:
                db_peer = session.query(PeerModel).filter(PeerModel.id == peer_id).first()
        
        return self._to_domain(db_peer) if db_peer else None
    
    async def update(self, peer: Peer) -> Peer:
        if self.session:
            session = self.session
            db_peer = session.query(PeerModel).filter(PeerModel.id == peer.id).first()
            if db_peer:
                db_peer.ip_address = peer.ip_address
                db_peer.grpc_port = peer.grpc_port
                db_peer.is_active = peer.status == PeerStatus.ACTIVE
                db_peer.last_heartbeat = peer.last_heartbeat
                session.flush()
                session.refresh(db_peer)
                return self._to_domain(db_peer)
        else:
            with db_connection.get_session() as session:
                db_peer = session.query(PeerModel).filter(PeerModel.id == peer.id).first()
                if db_peer:
                    db_peer.ip_address = peer.ip_address
                    db_peer.grpc_port = peer.grpc_port
                    db_peer.is_active = peer.status == PeerStatus.ACTIVE
                    db_peer.last_heartbeat = peer.last_heartbeat
                    session.flush()
                    session.refresh(db_peer)
                    return self._to_domain(db_peer)
        
        raise ValueError(f"Peer {peer.id} not found")
    
    async def delete(self, peer_id: str) -> bool:
        if self.session:
            session = self.session
            result = session.query(PeerModel).filter(PeerModel.id == peer_id).delete()
            return result > 0
        else:
            with db_connection.get_session() as session:
                result = session.query(PeerModel).filter(PeerModel.id == peer_id).delete()
                return result > 0
    
    async def list_all(self) -> List[Peer]:
        if self.session:
            db_peers = self.session.query(PeerModel).all()
        else:
            with db_connection.get_session() as session:
                db_peers = session.query(PeerModel).all()
        
        return [self._to_domain(peer) for peer in db_peers]
    
    async def get_active_peers(self) -> List[Peer]:
        """Obtener peers activos (heartbeat reciente)"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=2)
        
        if self.session:
            session = self.session
        else:
            session = next(db_connection.get_session())
        
        try:
            db_peers = session.query(PeerModel).filter(
                and_(
                    PeerModel.is_active == True,
                    PeerModel.last_heartbeat >= cutoff_time
                )
            ).all()
            
            return [self._to_domain(peer) for peer in db_peers]
        finally:
            if not self.session:
                session.close()
    
    async def update_heartbeat(self, peer_id: str) -> bool:
        if self.session:
            session = self.session
            result = session.query(PeerModel).filter(
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
    
    def _to_domain(self, db_peer: PeerModel) -> Peer:
        """Convertir modelo DB a modelo dominio"""
        return Peer(
            id=db_peer.id,
            ip_address=str(db_peer.ip_address),
            grpc_port=db_peer.grpc_port,
            status=PeerStatus.ACTIVE if db_peer.is_active else PeerStatus.INACTIVE,
            last_heartbeat=db_peer.last_heartbeat,
            created_at=db_peer.created_at
        )
