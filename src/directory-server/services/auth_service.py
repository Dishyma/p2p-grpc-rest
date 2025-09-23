import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import os
from sqlalchemy.orm import Session
from ..config import config
from ..models.peer import PeerModel

logger = logging.getLogger(__name__)

class AuthService:
    """Servicio de autenticación para peers del directory server"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        # Configuración JWT desde config centralizado
        self.secret_key = config.jwt_secret_key
        self.algorithm = config.jwt_algorithm
        self.token_expiry_hours = config.jwt_expiry_hours
        
    def _hash_password(self, password: str) -> str:
        """Hash simple de contraseña usando SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_peer(self, peer_name: str, password: str) -> Optional[Dict[str, Any]]:
        """Autentica un peer con peer_name y password"""
        try:
            peer = self.db.query(PeerModel).filter(PeerModel.peer_name == peer_name).first()
            if not peer:
                logger.warning(f"Peer no encontrado: {peer_name}")
                return None
                
            password_hash = self._hash_password(password)
            
            if password_hash != peer.password_hash:
                logger.warning(f"Contraseña incorrecta para peer: {peer_name}")
                return None
                
            logger.info(f"Peer autenticado exitosamente: {peer_name}")
            return {
                "peer_name": peer_name,
                "peer_id": str(peer.id),
                "role": "peer"
            }
        except Exception as e:
            logger.error(f"Error autenticando peer {peer_name}: {str(e)}")
            return None
    
    def create_token(self, peer_data: Dict[str, Any]) -> str:
        """Crea un token JWT para el peer autenticado"""
        try:
            payload = {
                "peer_name": peer_data["peer_name"],
                "peer_id": peer_data["peer_id"],
                "role": peer_data["role"],
                "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
                "iat": datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Token creado para peer: {peer_data['peer_name']}")
            return token
        except Exception as e:
            logger.error(f"Error creando token: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifica y decodifica un token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            logger.debug(f"Token verificado para peer: {payload.get('peer_name')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verificando token: {str(e)}")
            return None
    
    def get_peer_info(self, peer_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información del peer (sin contraseña)"""
        try:
            peer = self.db.query(PeerModel).filter(PeerModel.peer_name == peer_name).first()
            if peer:
                return {
                    "peer_name": peer.peer_name,
                    "peer_id": str(peer.id),
                    "role": "peer"
                }
            return None
        except Exception as e:
            logger.error(f"Error obteniendo info del peer {peer_name}: {str(e)}")
            return None
