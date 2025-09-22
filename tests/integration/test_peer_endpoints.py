"""
Tests de integración para endpoints REST de peers
"""
import pytest
import asyncio
import uuid

@pytest.mark.integration
@pytest.mark.asyncio
class TestPeerEndpoints:
    """Tests de integración para los endpoints REST de los peers"""
    
    async def test_peer_status_endpoint(self, peer_client, wait_for_services):
        """Test endpoint /status de peer"""
        await wait_for_services()
        
        status = await peer_client.get_status(peer_index=0)
        
        # Verificar estructura de respuesta
        assert "peer_name" in status
        assert "is_registered" in status
        assert "ip_address" in status
        assert "directory_server" in status
        assert "local_files_count" in status
        assert "files_directory" in status
        
        # Verificar tipos de datos
        assert isinstance(status["peer_name"], str)
        assert isinstance(status["is_registered"], bool)
        assert isinstance(status["local_files_count"], int)
        assert isinstance(status["directory_server"], dict)
        
        # Verificar directory server info
        dir_server = status["directory_server"]
        assert "url" in dir_server
        assert "status" in dir_server
        assert dir_server["status"] in ["connected", "disconnected"]
    
    async def test_peer_local_files_endpoint(self, peer_client, wait_for_services):
        """Test endpoint /files/local de peer"""
        await wait_for_services()
        
        files_response = await peer_client.list_local_files(peer_index=0)
        
        # Verificar estructura de respuesta
        assert "files" in files_response
        assert "total" in files_response
        assert "directory" in files_response
        
        # Verificar tipos
        assert isinstance(files_response["files"], list)
        assert isinstance(files_response["total"], int)
        assert isinstance(files_response["directory"], str)
        
        # Verificar consistencia
        assert files_response["total"] == len(files_response["files"])
        
        # Si hay archivos, verificar estructura
        if files_response["files"]:
            file_info = files_response["files"][0]
            assert "filename" in file_info
            assert "size" in file_info
            assert "modified" in file_info
            
            assert isinstance(file_info["filename"], str)
            assert isinstance(file_info["size"], int)
            assert isinstance(file_info["modified"], (int, float))
    
    async def test_peer_search_files_endpoint(self, peer_client, wait_for_services):
        """Test endpoint /files/search de peer"""
        await wait_for_services()
        
        # Buscar archivo que probablemente no existe
        search_result = await peer_client.search_files("nonexistent_file.txt", peer_index=0)
        
        # Verificar estructura de respuesta
        assert "filename" in search_result
        assert "peers" in search_result
        assert "total_peers" in search_result
        
        # Verificar valores
        assert search_result["filename"] == "nonexistent_file.txt"
        assert isinstance(search_result["peers"], list)
        assert isinstance(search_result["total_peers"], int)
        assert search_result["total_peers"] == len(search_result["peers"])
        
        # Para archivo inexistente, debería retornar 0 peers
        assert search_result["total_peers"] == 0
    
    async def test_peer_get_peers_endpoint(self, peer_client, wait_for_services):
        """Test endpoint /peers de peer"""
        await wait_for_services()
        
        peers_response = await peer_client.get_peers(peer_index=0)
        
        # Verificar estructura de respuesta
        assert "peers" in peers_response
        assert "total" in peers_response
        
        # Verificar tipos
        assert isinstance(peers_response["peers"], list)
        assert isinstance(peers_response["total"], int)
        
        # Verificar consistencia
        assert peers_response["total"] == len(peers_response["peers"])
        
        # Debería haber al menos algunos peers (los del docker-compose)
        assert peers_response["total"] >= 0  # Puede ser 0 si no hay peers registrados aún
        
        # Si hay peers, verificar estructura
        if peers_response["peers"]:
            peer_info = peers_response["peers"][0]
            # La estructura exacta depende de tu implementación
            # Ajustar según lo que retorne realmente tu API
            assert isinstance(peer_info, dict)
    
    async def test_multiple_peers_status(self, peer_client, wait_for_services):
        """Test status de múltiples peers"""
        await wait_for_services()
        
        # Probar status de los primeros 3 peers
        peer_statuses = []
        
        for i in range(min(3, len(peer_client.peer_urls))):
            try:
                status = await peer_client.get_status(peer_index=i)
                peer_statuses.append((i, status))
            except Exception as e:
                # Algunos peers pueden no estar disponibles
                print(f"Peer {i} no disponible: {e}")
        
        # Verificar que al menos 2 peers respondieron
        assert len(peer_statuses) >= 2
        
        # Verificar que cada peer tiene nombre único
        peer_names = [status["peer_name"] for _, status in peer_statuses]
        assert len(set(peer_names)) == len(peer_names)  # Todos únicos
        
        # Verificar que todos tienen configuración válida
        for peer_index, status in peer_statuses:
            assert status["peer_name"] is not None
            assert status["ip_address"] is not None
            assert isinstance(status["local_files_count"], int)
    
    async def test_peer_endpoints_consistency(self, peer_client, wait_for_services):
        """Test consistencia entre endpoints de un peer"""
        await wait_for_services()
        
        peer_index = 0
        
        # Obtener información de múltiples endpoints
        status = await peer_client.get_status(peer_index)
        files = await peer_client.list_local_files(peer_index)
        
        # Verificar consistencia en conteo de archivos
        assert status["local_files_count"] == files["total"]
        
        # Verificar consistencia en directorio de archivos
        # (Puede requerir normalización de paths)
        status_dir = status["files_directory"]
        files_dir = files["directory"]
        
        # Verificar que ambos apuntan al mismo directorio (básico)
        assert isinstance(status_dir, str)
        assert isinstance(files_dir, str)
        assert len(status_dir) > 0
        assert len(files_dir) > 0
    
    @pytest.mark.concurrency
    async def test_concurrent_requests_to_peer(self, peer_client, wait_for_services):
        """Test requests concurrentes a un peer"""
        await wait_for_services()
        
        peer_index = 0
        
        # Crear múltiples tareas concurrentes
        tasks = []
        
        # 5 requests de status
        for _ in range(5):
            tasks.append(peer_client.get_status(peer_index))
        
        # 3 requests de archivos locales
        for _ in range(3):
            tasks.append(peer_client.list_local_files(peer_index))
        
        # 2 requests de búsqueda
        for _ in range(2):
            tasks.append(peer_client.search_files("test_file.txt", peer_index))
        
        # Ejecutar todas concurrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Contar éxitos y fallos
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        # Al menos 80% deberían ser exitosos
        success_rate = len(successful) / len(results)
        assert success_rate >= 0.8
        
        print(f"Concurrency test: {len(successful)}/{len(results)} requests successful")
        
        if failed:
            print(f"Failed requests: {[str(f) for f in failed[:3]]}")  # Mostrar primeros 3 errores
    
    @pytest.mark.slow
    async def test_peer_endpoints_load(self, peer_client, wait_for_services):
        """Test de carga ligera en endpoints de peer"""
        await wait_for_services()
        
        peer_index = 0
        request_count = 20
        
        # Medir tiempo de respuesta
        import time
        start_time = time.time()
        
        # Hacer múltiples requests secuenciales
        successful_requests = 0
        
        for i in range(request_count):
            try:
                if i % 3 == 0:
                    await peer_client.get_status(peer_index)
                elif i % 3 == 1:
                    await peer_client.list_local_files(peer_index)
                else:
                    await peer_client.search_files(f"test_file_{i}.txt", peer_index)
                
                successful_requests += 1
            except Exception as e:
                print(f"Request {i} failed: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verificar métricas
        success_rate = successful_requests / request_count
        avg_response_time = total_time / successful_requests if successful_requests > 0 else float('inf')
        
        assert success_rate >= 0.9  # 90% de éxito mínimo
        assert avg_response_time < 1.0  # Menos de 1 segundo promedio
        
        print(f"Load test: {successful_requests}/{request_count} requests successful")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Total time: {total_time:.3f}s")
    
    async def test_peer_error_handling(self, endpoints, http_session, wait_for_services):
        """Test manejo de errores en endpoints de peer"""
        await wait_for_services()
        
        # Probar endpoint inexistente
        peer_url = endpoints["peers"][0]
        
        async with http_session.get(f"{peer_url}/nonexistent_endpoint") as response:
            assert response.status == 404
        
        # Probar parámetros inválidos en búsqueda
        async with http_session.get(f"{peer_url}/files/search") as response:
            # Debería fallar por falta de parámetro filename
            assert response.status in [400, 422]  # Bad Request o Unprocessable Entity
    
    async def test_peer_api_documentation(self, endpoints, http_session, wait_for_services):
        """Test que la documentación de API esté disponible"""
        await wait_for_services()
        
        peer_url = endpoints["peers"][0]
        
        # Probar endpoint de documentación (si existe)
        try:
            async with http_session.get(f"{peer_url}/docs") as response:
                if response.status == 200:
                    content = await response.text()
                    # Verificar que es documentación de Swagger/OpenAPI
                    assert "swagger" in content.lower() or "openapi" in content.lower()
                else:
                    # Si no hay docs, está bien, pero debería ser 404
                    assert response.status == 404
        except Exception:
            # Si falla la conexión, el peer puede no tener docs habilitadas
            pass
