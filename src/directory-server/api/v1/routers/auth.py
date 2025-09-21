from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
import logging
from ....services.auth_service import AuthService
from ...dependencies import get_auth_service, get_current_active_user
from ..schemas import LoginRequest, LoginResponse, TokenData

logger = logging.getLogger(__name__)
router = APIRouter(tags=["authentication"])

@router.post("/auth/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Endpoint de login para peers registrados
    """
    try:
        # Autenticar peer
        peer_data = auth_service.authenticate_peer(request.username, request.password)
        
        if not peer_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect peer name or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Crear token
        access_token = auth_service.create_token(peer_data)
        
        logger.info(f"Login exitoso para peer: {request.username}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400,  # 24 horas
            user_info={
                "peer_name": peer_data["peer_name"],
                "peer_id": peer_data["peer_id"],
                "role": peer_data["role"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.get("/auth/me")
def get_current_peer_info(
    current_user: TokenData = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Obtiene información del peer actual autenticado
    """
    try:
        peer_info = auth_service.get_peer_info(current_user.username)
        if not peer_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Peer not found"
            )
        
        return {
            "peer_name": peer_info["peer_name"],
            "peer_id": peer_info["peer_id"],
            "role": peer_info["role"],
            "authenticated": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo información del peer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/auth/validate")
def validate_token(
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Valida si un token es válido
    """
    return {
        "valid": True,
        "peer_name": current_user.username,
        "role": current_user.role
    }
