from sqlalchemy import Column, String, Integer, DateTime, Boolean, BigInteger, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import INET

Base = declarative_base()

class PeerModel(Base):
    __tablename__ = "peers"
    
    id = Column(String(50), primary_key=True)
    ip_address = Column(INET, nullable=False)
    grpc_port = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    files = relationship("PeerFileModel", back_populates="peer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Peer(id='{self.id}', ip='{self.ip_address}')>"

class PeerFileModel(Base):
    __tablename__ = "peer_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    peer_id = Column(String(50), ForeignKey("peers.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    file_hash = Column(String(64))  # SHA256 hash
    announced_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    peer = relationship("PeerModel", back_populates="files")
    
    # Unique constraint
    __table_args__ = (
        {"schema": "public"},
    )

# Índices adicionales para performance
Index('idx_peer_files_filename', PeerFileModel.filename)
Index('idx_peer_files_peer_id', PeerFileModel.peer_id)
Index('idx_peers_active_heartbeat', PeerModel.is_active, PeerModel.last_heartbeat)
