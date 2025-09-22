from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base
from .peer import PeerModel

class PeerFileModel(Base):
    __tablename__ = "peer_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    peer_id = Column(UUID(as_uuid=True), ForeignKey("peers.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    file_hash = Column(String(64))  # SHA256 hash
    announced_at = Column(DateTime(timezone=True), server_default=func.now())
    
    peer = relationship("PeerModel", back_populates="files")
    
    __table_args__ = (
        UniqueConstraint('peer_id', 'filename', name='uq_peer_file_peer_filename'),
        {"schema": "public"},
    )

Index('idx_peer_files_filename', PeerFileModel.filename)
Index('idx_peer_files_peer_id', PeerFileModel.peer_id)
