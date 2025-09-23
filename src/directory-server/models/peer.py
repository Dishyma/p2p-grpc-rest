from sqlalchemy import Column, String, Integer, DateTime, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import INET, UUID
import uuid
from .base import Base

class PeerModel(Base):
    __tablename__ = "peers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    peer_name = Column(String(50), unique=True, nullable=False)  # Nombre único del peer
    password_hash = Column(String(64), nullable=False)  # Hash SHA256 de la contraseña
    ip_address = Column(INET, nullable=False)
    grpc_port = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    files = relationship("PeerFileModel", back_populates="peer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Peer(id='{self.id}', name='{self.peer_name}', ip='{self.ip_address}')>"

Index('idx_peers_active_heartbeat', PeerModel.is_active, PeerModel.last_heartbeat)
Index('idx_peers_name', PeerModel.peer_name)
