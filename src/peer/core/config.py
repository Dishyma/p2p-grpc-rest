import os
import logging
from typing import Optional

class Config:
    """Configuración del Peer"""

    def __init__(self):
        self.peer_name = os.getenv("PEER_NAME", "peer_1")
        self.peer_password = os.getenv("PEER_PASSWORD", "peer123")
        self.peer_ip = os.getenv("PEER_IP", "0.0.0.0")
        
        self.grpc_download_port = int(os.getenv("GRPC_DOWNLOAD_PORT", "50051"))
        self.grpc_upload_port = int(os.getenv("GRPC_UPLOAD_PORT", "50061"))
        self.grpc_list_port = int(os.getenv("GRPC_LIST_PORT", "50071"))
        
        self.grpc_port = self.grpc_download_port
        
        self.rest_port: int = int(os.getenv("REST_PORT", "8001"))
        
        self.directory_server_url = os.getenv("DIRECTORY_SERVER_URL", "http://localhost:8080/api/v1")
        self.directory_username = self.peer_name
        self.directory_password = self.peer_password
        
        self.directory_access_token: Optional[str] = None
        
        self.files_directory = os.getenv("FILES_DIRECTORY", "data/peer_files")
        
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
        
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        self.peer_friend_primary_grpc = os.getenv("PEER_FRIEND_PRIMARY_GRPC")
        self.peer_friend_backup_grpc = os.getenv("PEER_FRIEND_BACKUP_GRPC")
        
        self.registered_peer_id = None
        
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

config = Config()