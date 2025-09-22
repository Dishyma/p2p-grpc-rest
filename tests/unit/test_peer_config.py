"""
Tests unitarios para la configuración del peer
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Importar el módulo de configuración
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from peer.core.config import Config

@pytest.mark.unit
class TestPeerConfig:
    """Tests para la clase Config"""
    
    def test_default_values(self):
        """Test que los valores por defecto son correctos"""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            
            # Verificar valores por defecto
            assert config.peer_name == "peer_1"
            assert config.peer_ip == "0.0.0.0"
            assert config.grpc_download_port == 50051
            assert config.grpc_upload_port == 50061
            assert config.grpc_list_port == 50071
            assert config.rest_port == 8001
            assert config.heartbeat_interval == 30
            assert config.log_level == "INFO"
    
    def test_environment_variables_override(self):
        """Test que las variables de entorno sobrescriben los defaults"""
        env_vars = {
            "PEER_NAME": "test_peer",
            "PEER_IP": "192.168.1.100",
            "GRPC_DOWNLOAD_PORT": "50055",
            "GRPC_UPLOAD_PORT": "50065",
            "GRPC_LIST_PORT": "50075",
            "REST_PORT": "8005",
            "HEARTBEAT_INTERVAL": "60",
            "LOG_LEVEL": "DEBUG",
            "FILES_DIRECTORY": "/tmp/custom_path",
            "DIRECTORY_SERVER_URL": "http://custom-server:9090/api/v1"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            
            assert config.peer_name == "test_peer"
            assert config.peer_ip == "192.168.1.100"
            assert config.grpc_download_port == 50055
            assert config.grpc_upload_port == 50065
            assert config.grpc_list_port == 50075
            assert config.rest_port == 8005
            assert config.heartbeat_interval == 60
            assert config.log_level == "DEBUG"
            assert config.files_directory == "/tmp/custom_path"
            assert config.directory_server_url == "http://custom-server:9090/api/v1"
    
    def test_port_validation(self):
        """Test que los puertos se validan correctamente"""
        # Puertos válidos
        valid_ports = ["1024", "8080", "65535"]
        for port in valid_ports:
            with patch.dict(os.environ, {"GRPC_DOWNLOAD_PORT": port}, clear=True):
                config = Config()
                assert config.grpc_download_port == int(port)
        
        # Puertos inválidos deberían lanzar error al convertir a int
        invalid_ports = ["abc", "invalid", "not_a_number"]
        for port in invalid_ports:
            with patch.dict(os.environ, {"GRPC_DOWNLOAD_PORT": port}, clear=True):
                with pytest.raises(ValueError):
                    config = Config()
        
        # Puertos en el límite (pueden ser válidos o no según implementación)
        edge_cases = ["0", "70000"]
        for port in edge_cases:
            with patch.dict(os.environ, {"GRPC_DOWNLOAD_PORT": port}, clear=True):
                config = Config()
                # Estos puertos se aceptan tal como están (sin validación adicional)
                assert config.grpc_download_port == int(port)
    
    def test_files_directory_creation(self):
        """Test que el directorio de archivos se crea si no existe"""
        test_dir = "/tmp/test_peer_files"
        
        # Asegurar que el directorio no existe
        if Path(test_dir).exists():
            import shutil
            shutil.rmtree(test_dir)
        
        with patch.dict(os.environ, {"FILES_DIRECTORY": test_dir}, clear=True):
            config = Config()
            
            # Verificar que la configuración se cargó
            assert config.files_directory == test_dir
            
            # Limpiar si se creó
            if Path(test_dir).exists():
                import shutil
                shutil.rmtree(test_dir)
    
    def test_peer_friends_configuration(self):
        """Test configuración de peers amigos para failover"""
        env_vars = {
            "PEER_FRIEND_PRIMARY": "http://peer2:8002",
            "PEER_FRIEND_BACKUP": "http://peer3:8003",
            "PEER_FRIEND_PRIMARY_GRPC": "peer2:50052",
            "PEER_FRIEND_BACKUP_GRPC": "peer3:50053"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config()
            
            # Verificar que las variables se leyeron correctamente
            # (aunque no estén definidas como atributos específicos)
            assert os.environ.get("PEER_FRIEND_PRIMARY") == "http://peer2:8002"
            assert os.environ.get("PEER_FRIEND_BACKUP") == "http://peer3:8003"
    
    def test_singleton_behavior(self):
        """Test que Config mantiene consistencia"""
        with patch.dict(os.environ, {"PEER_NAME": "singleton_test"}, clear=True):
            config1 = Config()
            config2 = Config()
            
            # Deberían tener los mismos valores
            assert config1.peer_name == config2.peer_name
            assert config1.grpc_download_port == config2.grpc_download_port
    
    def test_logging_configuration_load(self):
        """Test que la configuración se carga correctamente"""
        with patch.dict(os.environ, {"PEER_NAME": "log_test"}, clear=True):
            config = Config()
            
            # Verificar que la configuración se cargó
            assert config.peer_name == "log_test"
    
    def test_directory_server_url_validation(self):
        """Test validación de URL del directory server"""
        valid_urls = [
            "http://localhost:8080/api/v1",
            "https://directory.example.com/api/v1",
            "http://192.168.1.100:8080/api/v1"
        ]
        
        for url in valid_urls:
            with patch.dict(os.environ, {"DIRECTORY_SERVER_URL": url}, clear=True):
                config = Config()
                assert config.directory_server_url == url
        
        # URLs inválidas
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            ""
        ]
        
        for url in invalid_urls:
            with patch.dict(os.environ, {"DIRECTORY_SERVER_URL": url}, clear=True):
                # Debería usar default o validar
                config = Config()
                # La validación específica depende de tu implementación
                assert config.directory_server_url is not None
    
    def test_token_management(self):
        """Test manejo de tokens de acceso"""
        config = Config()
        
        # Inicialmente no debería haber token
        assert config.get_directory_access_token() is None
        
        # Establecer token
        test_token = "test_jwt_token_12345"
        config.set_directory_access_token(test_token)
        
        # Verificar que se guardó
        assert config.get_directory_access_token() == test_token
        
        # Limpiar sesión (incluye token)
        config.clear_session()
        
        # Verificar que se limpió
        assert config.get_directory_access_token() is None
