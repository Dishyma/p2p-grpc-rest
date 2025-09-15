from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import ipaddress

class PeerRegisterRequest(BaseModel):
    peer_id: str = Field(..., min_length=1, max_length=50)
    ip_address: str = Field(..., description="IP address of the peer")
    grpc_port: int = Field(..., ge=1, le=65535)
    files: List[str] = Field(default=[], description="List of files this peer has")
    
    @validator('ip_address')
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

class PeerResponse(BaseModel):
    peer_id: str
    ip_address: str
    grpc_port: int
    is_active: bool
    last_heartbeat: datetime
    
    class Config:
        from_attributes = True

class FileSearchResponse(BaseModel):
    filename: str
    peers: List[PeerResponse]
    total_peers: int

class FileAnnounceRequest(BaseModel):
    peer_id: str = Field(..., min_length=1)
    files: List[str] = Field(..., min_items=1)

class HeartbeatRequest(BaseModel):
    peer_id: str = Field(..., min_length=1)

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime
    database_status: str
    active_peers: int
