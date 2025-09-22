"""
Tests simples para verificar que los imports funcionan correctamente
"""
import pytest
import sys
from pathlib import Path

# Agregar src al path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

@pytest.mark.unit
class TestImports:
    """Tests para verificar imports de la nueva arquitectura"""
    
    def test_config_import(self):
        """Test que se puede importar Config"""
        from peer.core.config import Config
        config = Config()
        assert config.peer_name is not None
        assert config.grpc_download_port > 0
        assert config.grpc_upload_port > 0
        assert config.grpc_list_port > 0
    
    def test_directory_client_import(self):
        """Test que se puede importar DirectoryClient"""
        from peer.clients.rest.directory_client import DirectoryClient
        client = DirectoryClient()
        assert client is not None
        assert hasattr(client, 'base_url')
    
    def test_peer_grpc_client_import(self):
        """Test que se puede importar PeerGrpcClient"""
        from peer.clients.grpc.peer_client import PeerGrpcClient
        client = PeerGrpcClient()
        assert client is not None
        assert hasattr(client, 'default_timeout')
        assert hasattr(client, 'chunk_size')
        assert client.default_timeout > 0
        assert client.chunk_size > 0
    
    def test_file_discovery_import(self):
        """Test que se puede importar FileDiscoveryService"""
        from peer.clients.grpc.file_discovery import FileDiscoveryService
        service = FileDiscoveryService()
        assert service is not None
        assert hasattr(service, 'grpc_client')
        assert hasattr(service, 'max_retries')
    
    def test_peer_manager_import(self):
        """Test que se puede importar PeerManager"""
        from peer.core.peer_manager import PeerManager
        manager = PeerManager()
        assert manager is not None
        assert hasattr(manager, 'upload_servicer')
        assert hasattr(manager, 'download_servicer')
        assert hasattr(manager, 'list_servicer')
    
    def test_grpc_services_import(self):
        """Test que se pueden importar los servicios gRPC"""
        from peer.services.grpc.download_service import DownloadFileServicer
        from peer.services.grpc.upload_service import UploadFileServicer
        from peer.services.grpc.list_service import ListFilesServicer
        
        download_service = DownloadFileServicer()
        upload_service = UploadFileServicer()
        list_service = ListFilesServicer()
        
        assert download_service is not None
        assert upload_service is not None
        assert list_service is not None
        
        assert hasattr(download_service, 'files_directory')
        assert hasattr(upload_service, 'files_directory')
        assert hasattr(list_service, 'files_directory')
    
    def test_api_server_import(self):
        """Test que se puede importar el módulo del API server"""
        # Solo importar el módulo, no crear la app
        import peer.services.rest.api_server as api_server
        assert hasattr(api_server, 'PeerStatus')
        assert hasattr(api_server, 'FileInfo')
        assert hasattr(api_server, 'LocalFilesResponse')
    
    def test_path_setup_import(self):
        """Test que path_setup funciona correctamente"""
        from peer.core.path_setup import setup_paths
        
        # Llamar setup_paths no debería dar error
        setup_paths()
        
        # Verificar que los paths están en sys.path
        import sys
        src_paths = [p for p in sys.path if 'src' in p]
        gen_paths = [p for p in sys.path if 'generated' in p]
        
        assert len(src_paths) > 0, "Path de src no encontrado"
        assert len(gen_paths) > 0, "Path de generated no encontrado"
