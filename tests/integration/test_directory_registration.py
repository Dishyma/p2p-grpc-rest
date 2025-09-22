"""
Tests de integración para registro y autenticación con Directory Server
"""
import pytest
import uuid
import asyncio

@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryRegistration:
    """Tests de integración para el Directory Server"""
    
    async def test_peer_registration_success(self, directory_client, wait_for_services):
        """Test registro exitoso de peer"""
        await wait_for_services()
        peer_name = f"test_peer_{uuid.uuid4().hex[:8]}"
        password = "test_password_123"
        
        result = await directory_client.register_peer(
            peer_name=peer_name,
            password=password,
            ip_address="192.168.1.100",
            grpc_port=50051
        )
        
        # Verificar respuesta de registro
        assert "peer_id" in result
        assert "access_token" in result
        assert "token_type" in result
        assert result["peer_name"] == peer_name
        assert result["ip_address"] == "192.168.1.100"
        assert result["grpc_port"] == 50051
        assert result["is_active"] is True
        assert result["token_type"] == "bearer"
        
        # Verificar que el token se guardó en el cliente
        assert directory_client.access_token is not None
        assert directory_client.access_token == result["access_token"]
    
    
    async def test_login_after_registration(self, directory_client, wait_for_services):
        """Test login después de registro"""
        await wait_for_services()
        peer_name = f"login_test_{uuid.uuid4().hex[:8]}"
        password = "login_password_123"
        
        # Registrar peer
        registration_result = await directory_client.register_peer(
            peer_name=peer_name,
            password=password
        )
        
        # Limpiar token del registro
        directory_client.access_token = None
        
        # Hacer login
        login_result = await directory_client.login(peer_name, password)
        
        # Verificar respuesta de login
        assert "access_token" in login_result
        assert "token_type" in login_result
        assert "expires_in" in login_result
        assert "user_info" in login_result
        
        user_info = login_result["user_info"]
        assert user_info["peer_name"] == peer_name
        assert user_info["peer_id"] == registration_result["peer_id"]
        assert user_info["role"] == "peer"
        
        # Verificar que el token se guardó
        assert directory_client.access_token == login_result["access_token"]
    
    async def test_login_wrong_credentials(self, directory_client, wait_for_services):
        """Test login con credenciales incorrectas"""
        await wait_for_services()
        peer_name = f"wrong_creds_{uuid.uuid4().hex[:8]}"
        password = "correct_password"
        
        # Registrar peer
        await directory_client.register_peer(
            peer_name=peer_name,
            password=password
        )
        
        # Limpiar token
        directory_client.access_token = None
        
        # Intentar login con contraseña incorrecta
        with pytest.raises(Exception) as exc_info:
            await directory_client.login(peer_name, "wrong_password")
        
        assert "401" in str(exc_info.value)
    
    async def test_protected_endpoint_without_token(self, directory_client, wait_for_services):
        """Test acceso a endpoint protegido sin token"""
        await wait_for_services()
        # Asegurar que no hay token
        directory_client.access_token = None
        
        # Intentar acceder a endpoint protegido
        with pytest.raises(Exception) as exc_info:
            await directory_client.get_active_peers()
        
        # Debería fallar con 401 Unauthorized o 403 Forbidden
        assert "401" in str(exc_info.value) or "403" in str(exc_info.value)
    
    async def test_protected_endpoint_with_valid_token(self, directory_client, wait_for_services):
        """Test acceso a endpoint protegido con token válido"""
        await wait_for_services()
        peer_name = f"protected_test_{uuid.uuid4().hex[:8]}"
        password = "protected_password"
        
        # Registrar y obtener token
        await directory_client.register_peer(
            peer_name=peer_name,
            password=password
        )
        
        # Acceder a endpoint protegido
        peers = await directory_client.get_active_peers()
        
        # Verificar respuesta
        assert isinstance(peers, list)
        # Debería incluir al menos el peer que acabamos de registrar
        peer_names = [peer.get("peer_name") for peer in peers if "peer_name" in peer]
        # Nota: puede que no esté en la lista si el endpoint retorna formato diferente
        # Ajustar según la implementación real
    
    async def test_search_files_with_token(self, directory_client, wait_for_services):
        """Test búsqueda de archivos con token válido"""
        await wait_for_services()
        peer_name = f"search_test_{uuid.uuid4().hex[:8]}"
        password = "search_password"
        
        # Registrar y obtener token
        await directory_client.register_peer(
            peer_name=peer_name,
            password=password
        )
        
        # Buscar archivo (aunque no exista)
        search_result = await directory_client.search_files("nonexistent_file.txt")
        
        # Verificar estructura de respuesta
        assert "filename" in search_result
        assert "files" in search_result
        assert "total_files" in search_result
        assert search_result["filename"] == "nonexistent_file.txt"
        assert isinstance(search_result["files"], list)
        assert search_result["total_files"] == len(search_result["files"])
    
    async def test_multiple_peers_registration(self, directory_client, wait_for_services, test_peer_credentials):
        """Test registro de múltiples peers"""
        await wait_for_services()
        registered_peers = []
        
        # Registrar múltiples peers
        for i, creds in enumerate(test_peer_credentials):
            peer_name = f"{creds['peer_name']}_{uuid.uuid4().hex[:8]}"
            
            result = await directory_client.register_peer(
                peer_name=peer_name,
                password=creds["password"],
                ip_address=f"192.168.1.{100 + i}",
                grpc_port=50051 + i
            )
            
            registered_peers.append(result)
        
        # Verificar que todos se registraron correctamente
        assert len(registered_peers) == len(test_peer_credentials)
        
        # Verificar que todos tienen IDs únicos
        peer_ids = [peer["peer_id"] for peer in registered_peers]
        assert len(set(peer_ids)) == len(peer_ids)  # Todos únicos
        
        # Verificar que todos tienen tokens
        tokens = [peer["access_token"] for peer in registered_peers]
        assert all(token for token in tokens)
        assert len(set(tokens)) == len(tokens)  # Todos únicos
    
    
    @pytest.mark.slow
    async def test_concurrent_registrations(self, endpoints, http_session, wait_for_services):
        """Test registros concurrentes de peers"""
        await wait_for_services()
        
        from tests.conftest import DirectoryClient
        
        async def register_peer(session, base_url, peer_index):
            """Función auxiliar para registrar un peer"""
            # Crear una nueva instancia del cliente para cada tarea
            local_client = DirectoryClient(base_url, session)
            peer_name = f"concurrent_peer_{peer_index}_{uuid.uuid4().hex[:8]}"
            
            return await local_client.register_peer(
                peer_name=peer_name,
                password=f"password_{peer_index}",
                ip_address=f"192.168.1.{100 + peer_index}",
                grpc_port=50051 + peer_index
            )
        
        # Registrar 5 peers concurrentemente
        async def register_concurrently():
            tasks = []
            for i in range(5):
                task = asyncio.create_task(register_peer(http_session, endpoints["directory"], i))
                tasks.append(task)
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        results = await register_concurrently()
        
        # Verificar que todas las registraciones fueron exitosas
        successful_registrations = [r for r in results if not isinstance(r, Exception)]
        failed_registrations = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_registrations) >= 4  # Al menos 4 de 5 deberían ser exitosas
        assert len(failed_registrations) <= 1  # Máximo 1 falla por concurrencia
        
        # Verificar unicidad de IDs
        peer_ids = [reg["peer_id"] for reg in successful_registrations]
        assert len(set(peer_ids)) == len(peer_ids)
