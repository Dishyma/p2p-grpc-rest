import os
import logging
from typing import Optional

class Config:
    """Configuración del Peer"""

    def __init__(self):
        # Configuración básica
        self.peer_name = os.getenv("PEER_NAME", "peer_1")  # Nombre del peer (username)
        self.peer_password = os.getenv("PEER_PASSWORD", "peer123")  # Password del peer
        self.peer_ip = os.getenv("PEER_IP", "0.0.0.0")
        self.grpc_port = int(os.getenv("GRPC_PORT", "50051"))
        # REST API Port
        self.rest_port: int = int(os.getenv("REST_PORT", "8001"))
        
        # Configuración del directory server
        self.directory_server_url = os.getenv("DIRECTORY_SERVER_URL", "http://localhost:8080/api/v1")
        # Credenciales del peer para autenticación (mismo peer_name y password)
        self.directory_username = self.peer_name
        self.directory_password = self.peer_password
        # Token JWT obtenido tras login
        self.directory_access_token: Optional[str] = None
        
        # Configuración de archivos
        self.files_directory = os.getenv("FILES_DIRECTORY", "data/peer_files")
        
        # Configuración de heartbeat
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
        
        # Configuración de logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Configuración de peers amigos para redundancia/failover
        self.peer_friend_primary_grpc = os.getenv("PEER_FRIEND_PRIMARY_GRPC")
        self.peer_friend_backup_grpc = os.getenv("PEER_FRIEND_BACKUP_GRPC")
        
        # ID del peer registrado (se establece dinámicamente)
        self.registered_peer_id = None
        
        # Asegurar que el directorio de archivos exista
        os.makedirs(self.files_directory, exist_ok=True)
    
    def set_registered_peer_id(self, peer_id: str):
        """Establecer el ID del peer una vez registrado"""
        self.registered_peer_id = peer_id
        
    def get_registered_peer_id(self) -> str:
        """Obtener el ID del peer registrado"""
        return self.registered_peer_id

    def clear_session(self):
        """Limpia los datos de la sesión actual (token y peer_id)."""
        self.directory_access_token = None
        self.registered_peer_id = None
        logging.info("Sesión local del peer limpiada.")

    def set_directory_access_token(self, token: Optional[str]):
        """Guardar o limpiar el token de acceso JWT del directory server"""
        self.directory_access_token = token

    def get_directory_access_token(self) -> Optional[str]:
        """Obtener el token de acceso JWT del directory server"""
        return self.directory_access_token

# Instancia global de configuración
config = Config()