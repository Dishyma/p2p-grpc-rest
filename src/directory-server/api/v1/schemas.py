from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import ipaddress
import uuid

class PeerRegisterRequest(BaseModel):
    peer_name: str = Field(..., description="Nombre único del peer (username)")
    password: str = Field(..., description="Contraseña del peer")
    ip_address: str = Field(..., description="IP address of the peer")
    grpc_port: int = Field(..., ge=1, le=65535)
    
    @validator('ip_address')
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

class PeerResponse(BaseModel):
    peer_id: uuid.UUID
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

class FileMetadata(BaseModel):
    filename: str
    size: int
    hash: str

class FileAnnounceRequest(BaseModel):
    peer_id: str = Field(...)
    files: List[FileMetadata] = Field(..., min_items=1)

class HeartbeatRequest(BaseModel):
    peer_id: str = Field(...)

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime
    database_status: str
    active_peers: int

# Esquemas de autenticación
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 horas en segundos
    user_info: dict

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class SuccessMessage(BaseModel):
    message: str
