from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class PeerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"

@dataclass
class Peer:
    """Modelo de dominio para un Peer"""
    id: str
    ip_address: str
    grpc_port: int
    status: PeerStatus
    last_heartbeat: datetime
    created_at: datetime

@dataclass
class FileInfo:
    """Modelo de dominio para información de archivo"""
    filename: str
    size: int
    hash: str
    peer_id: str
    announced_at: datetime

@dataclass
class FileTransferRequest:
    """Request para transferencia de archivo"""
    filename: str
    requesting_peer_id: str
    target_peer_id: str