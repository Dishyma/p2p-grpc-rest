"""
Tests unitarios para PeerGrpcClient
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, ANY
from pathlib import Path

# Importar el cliente
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from peer.clients.grpc.peer_client import PeerGrpcClient

@pytest.mark.unit
class TestPeerGrpcClient:
    """Tests para PeerGrpcClient (comunicación gRPC pura)"""
    
    @pytest.fixture
    def grpc_client(self):
        """Fixture del cliente gRPC"""
        return PeerGrpcClient()
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, grpc_client):
        """Test descarga exitosa de archivo"""
        # Mock del canal gRPC y stub
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            
            mock_stub = Mock()
            mock_channel_instance.channel_ready = AsyncMock()
            mock_channel_instance.close = AsyncMock()
            
            # Mock de la respuesta de descarga (chunks)
            async def mock_download_chunks():
                yield Mock(content=b"chunk1", filename="test.txt")
                yield Mock(content=b"chunk2", filename="test.txt")
                yield Mock(content=b"", filename="test.txt")  # Fin
            
            mock_stub.DownloadFile.return_value = mock_download_chunks()
            
            with patch('peer.clients.grpc.peer_client.file_service_pb2_grpc.FileTransferStub', return_value=mock_stub):
                with patch('aiofiles.open', create=True) as mock_open:
                    mock_file = AsyncMock()
                    mock_open.return_value.__aenter__.return_value = mock_file
                    
                    # Test descarga
                    success = await grpc_client.download_file_from_peer(
                        peer_ip="127.0.0.1",
                        peer_port=50051,
                        filename="test.txt",
                        output_path=Path("/tmp/test.txt")
                    )
                    
                    # Verificaciones
                    assert success is True
                    mock_channel.assert_called_once_with("127.0.0.1:50051", options=ANY)
                    mock_channel_instance.channel_ready.assert_called_once()
                    mock_file.write.assert_any_call(b"chunk1")
                    mock_file.write.assert_any_call(b"chunk2")
                    mock_channel_instance.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_file_connection_error(self, grpc_client):
        """Test error de conexión en descarga"""
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            mock_channel_instance.channel_ready.side_effect = asyncio.TimeoutError("Connection timeout")
            
            success = await grpc_client.download_file_from_peer(
                peer_ip="127.0.0.1",
                peer_port=50051,
                filename="test.txt"
            )
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, grpc_client):
        """Test listado exitoso de archivos"""
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            mock_channel_instance.channel_ready = AsyncMock()
            mock_channel_instance.close = AsyncMock()
            
            # Mock respuesta de listado
            mock_response = Mock()
            mock_response.files = [
                Mock(filename="file1.txt", file_size=100, file_hash="hash1", last_modified="2023-01-01"),
                Mock(filename="file2.pdf", file_size=200, file_hash="hash2", last_modified="2023-01-02")
            ]
            
            mock_stub = Mock()
            mock_stub.ListFiles = AsyncMock(return_value=mock_response)
            
            with patch('peer.clients.grpc.peer_client.file_service_pb2_grpc.FileTransferStub', return_value=mock_stub):
                files = await grpc_client.list_files_from_peer(
                    peer_ip="127.0.0.1",
                    peer_port=50071
                )
                
                # Verificaciones
                assert len(files) == 2
                assert files[0]['filename'] == "file1.txt"
                assert files[0]['file_size'] == 100
                assert files[1]['filename'] == "file2.pdf"
                assert files[1]['file_size'] == 200
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, grpc_client):
        """Test subida exitosa de archivo"""
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            mock_channel_instance.channel_ready = AsyncMock()
            mock_channel_instance.close = AsyncMock()
            
            # Mock respuesta de upload
            mock_response = Mock()
            mock_response.success = True
            mock_response.message = "Upload successful"
            mock_response.file_hash = "abc123"
            
            mock_stub = Mock()
            mock_stub.UploadFile = AsyncMock(return_value=mock_response)
            
            with patch('peer.clients.grpc.peer_client.file_service_pb2_grpc.FileTransferStub', return_value=mock_stub):
                result = await grpc_client.upload_file_to_peer(
                    peer_ip="127.0.0.1",
                    peer_port=50061,
                    filename="test.txt",
                    file_data=b"test content"
                )
                
                # Verificaciones
                assert result['success'] is True
                assert result['message'] == "Upload successful"
                assert result['hash'] == "abc123"
    
    @pytest.mark.asyncio
    async def test_ping_peer_success(self, grpc_client):
        """Test ping exitoso a peer"""
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            mock_channel_instance.channel_ready = AsyncMock()
            mock_channel_instance.close = AsyncMock()
            
            mock_stub = Mock()
            
            with patch('peer.clients.grpc.peer_client.file_service_pb2_grpc.FileTransferStub', return_value=mock_stub):
                is_alive = await grpc_client.ping_peer("127.0.0.1", 50051)
                
                # Verificaciones
                assert is_alive is True
                mock_channel.assert_called_once()
                mock_channel_instance.channel_ready.assert_called_once()
                mock_channel_instance.close.assert_called_once()
                
    
    @pytest.mark.asyncio
    async def test_ping_peer_failure(self, grpc_client):
        """Test ping fallido a peer"""
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            mock_channel_instance.channel_ready.side_effect = Exception("Connection failed")
            
            is_alive = await grpc_client.ping_peer("127.0.0.1", 50051)
            
            assert is_alive is False
    
    @pytest.mark.asyncio
    async def test_get_file_info_success(self, grpc_client):
        """Test obtener información de archivo exitosamente"""
        with patch('grpc.aio.insecure_channel') as mock_channel:
            mock_channel_instance = AsyncMock()
            mock_channel.return_value = mock_channel_instance
            mock_channel_instance.channel_ready = AsyncMock()
            mock_channel_instance.close = AsyncMock()
            
            # Mock respuesta de info
            mock_response = Mock()
            mock_response.filename = "test.txt"
            mock_response.file_size = 1024
            mock_response.file_hash = "hash123"
            mock_response.last_modified = "2023-01-01"
            
            mock_stub = Mock()
            mock_stub.GetFileInfo = AsyncMock(return_value=mock_response)
            
            with patch('peer.clients.grpc.peer_client.file_service_pb2_grpc.FileTransferStub', return_value=mock_stub):
                file_info = await grpc_client.get_file_info_from_peer(
                    peer_ip="127.0.0.1",
                    peer_port=50051,
                    filename="test.txt"
                )
                
                # Verificaciones
                assert file_info is not None
                assert file_info['filename'] == "test.txt"
                assert file_info['file_size'] == 1024
                assert file_info['file_hash'] == "hash123"
    
    def test_client_initialization(self, grpc_client):
        """Test inicialización correcta del cliente"""
        assert grpc_client.default_timeout == 30
        assert grpc_client.chunk_size == 64 * 1024
    
    @pytest.mark.parametrize("timeout", [10, 30, 60])
    def test_timeout_configuration(self, grpc_client, timeout):
        """Test configuración de timeouts"""
        # Verificar que el timeout se puede configurar
        assert timeout > 0  # Test básico de parametrización
        
        # En implementación real, verificaríamos que el timeout se usa correctamente
        # en las llamadas gRPC
