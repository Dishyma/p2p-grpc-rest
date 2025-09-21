from functools import lru_cache
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..contextdb.connection import get_db_session
from ..repositories.peer_repository import PeerRepository
from ..repositories.file_repository import PeerFileRepository
from ..services.directory_service import DirectoryService
from ..services.auth_service import AuthService
from .v1.schemas import TokenData

def get_peer_repository(db: Session = Depends(get_db_session)) -> PeerRepository:
    return PeerRepository(db)

def get_file_repository(db: Session = Depends(get_db_session)) -> PeerFileRepository:
    return PeerFileRepository(db)

def get_directory_service(
    peer_repo: PeerRepository = Depends(get_peer_repository),
    file_repo: PeerFileRepository = Depends(get_file_repository)
) -> DirectoryService:
    return DirectoryService(peer_repo, file_repo)

# Esquema de seguridad HTTP Bearer
security = HTTPBearer()

def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    """Dependency para obtener el servicio de autenticación"""
    return AuthService(db)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_svc: AuthService = Depends(get_auth_service)
) -> TokenData:
    """Dependency para obtener el usuario actual desde el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = auth_svc.verify_token(token)
        
        if payload is None:
            raise credentials_exception
            
        peer_name: str = payload.get("peer_name")
        peer_id: str = payload.get("peer_id")
        role: str = payload.get("role")
        
        if peer_name is None or peer_id is None:
            raise credentials_exception
            
        return TokenData(username=peer_name, peer_id=peer_id, role=role)
    except Exception:
        raise credentials_exception

def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Dependency para obtener el usuario actual activo"""
    return current_user
