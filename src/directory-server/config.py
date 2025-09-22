import os
from typing import Optional

class DirectoryServerConfig:
    """Configuración centralizada del Directory Server"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://p2p:unaClav3@localhost:5432/p2p_db"
        )
        self.sql_echo = os.getenv("SQL_ECHO", "false").lower() == "true"
        
        self.port = int(os.getenv("PORT", "8000"))
        self.host = os.getenv("HOST", "0.0.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.reload = self.environment == "development"
        
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "p2p-directory-secret-key-2024")
        self.jwt_algorithm = "HS256"
        self.jwt_expiry_hours = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
        
        # Configuración de la aplicación
        self.app_title = "P2P Directory Server"
        self.app_description = "Servidor de directorio para red P2P"
        self.app_version = "1.0.0"
        self.api_prefix = "/api/v1"

config = DirectoryServerConfig()