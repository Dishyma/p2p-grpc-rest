"""
Tests de concurrencia para la nueva arquitectura
Reemplazo de test_concurrency.py original
"""
import pytest
import asyncio
import aiohttp
import time
from typing import List, Tuple

@pytest.mark.integration
@pytest.mark.concurrency
@pytest.mark.asyncio
class TestConcurrencyNew:
    """Tests de concurrencia usando nueva arquitectura"""
    
    async def test_peer_concurrent_operations_new_arch(self, endpoints, wait_for_services):
        """Test operaciones concurrentes usando nueva estructura"""
        await wait_for_services()
        
        peer_url = endpoints["peers"][0]
        operations_count = 15
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Crear tareas concurrentes con nueva arquitectura
            for i in range(operations_count):
                if i % 4 == 0:
                    task = self._test_status_operation(session, peer_url, f"op{i}")
                elif i % 4 == 1:
                    task = self._test_local_files_operation(session, peer_url, f"op{i}")
                elif i % 4 == 2:
                    task = self._test_peers_list_operation(session, peer_url, f"op{i}")
                else:
                    task = self._test_file_search_operation(session, peer_url, f"op{i}", f"test_file_{i}.txt")
                
                tasks.append(task)
            
            # Ejecutar todas las tareas concurrentemente
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analizar resultados con asserts
            successful = sum(1 for r in results if r is True)
            failed = sum(1 for r in results if isinstance(r, Exception))
            total_time = end_time - start_time
            
            # Asserts para verificar concurrencia
            assert successful >= operations_count * 0.7, f"Solo {successful}/{operations_count} operaciones exitosas"
            assert total_time < 30, f"Tiempo excesivo: {total_time}s"
            assert failed <= operations_count * 0.3, f"Demasiados fallos: {failed}"
            
            # Métricas de performance
            avg_time = total_time / operations_count
            success_rate = successful / operations_count
            
            print(f"✅ Concurrencia: {successful}/{operations_count} exitosas")
            print(f"⏱️  Tiempo total: {total_time:.2f}s, promedio: {avg_time:.3f}s/op")
            print(f"📈 Tasa de éxito: {success_rate:.1%}")
            
            # Asserts de performance
            assert avg_time < 2.0, f"Tiempo promedio muy alto: {avg_time:.3f}s"
            assert success_rate >= 0.7, f"Tasa de éxito muy baja: {success_rate:.1%}"
    
    async def test_cross_peer_operations_new_arch(self, endpoints, wait_for_services):
        """Test operaciones cruzadas entre peers con nueva arquitectura"""
        await wait_for_services()
        
        # Usar todos los peers disponibles
        peer_urls = endpoints["peers"][:4]  # Máximo 4 peers
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Cada peer busca archivos diferentes
            test_files = ["video.mp4", "document.pdf", "image.jpg", "data.txt"]
            
            for i, peer_url in enumerate(peer_urls):
                filename = test_files[i % len(test_files)]
                task = self._test_file_search_operation(session, peer_url, f"peer{i}", filename)
                tasks.append(task)
            
            # Ejecutar búsquedas concurrentes
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful = sum(1 for r in results if r is True)
            total_time = end_time - start_time
            
            # Asserts para operaciones cruzadas
            assert successful >= len(peer_urls) * 0.5, f"Muy pocas búsquedas exitosas: {successful}/{len(peer_urls)}"
            assert total_time < 20, f"Tiempo excesivo para búsquedas cruzadas: {total_time}s"
            
            print(f"🔍 Búsquedas cruzadas: {successful}/{len(peer_urls)} exitosas en {total_time:.2f}s")
    
    @pytest.mark.parametrize("load_level", [5, 10, 20])
    async def test_scalable_load_new_arch(self, endpoints, wait_for_services, load_level):
        """Test carga escalable con nueva arquitectura"""
        await wait_for_services()
        
        peer_url = endpoints["peers"][0]
        
        async with aiohttp.ClientSession() as session:
            # Crear tareas de diferentes tipos
            tasks = []
            
            # 60% operaciones ligeras (status)
            light_ops = int(load_level * 0.6)
            for i in range(light_ops):
                tasks.append(self._test_status_operation(session, peer_url, f"light_{i}"))
            
            # 30% operaciones medianas (archivos)
            medium_ops = int(load_level * 0.3)
            for i in range(medium_ops):
                tasks.append(self._test_local_files_operation(session, peer_url, f"medium_{i}"))
            
            # 10% operaciones pesadas (búsqueda)
            heavy_ops = max(1, int(load_level * 0.1))
            for i in range(heavy_ops):
                tasks.append(self._test_file_search_operation(session, peer_url, f"heavy_{i}", f"search_{i}.txt"))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful = sum(1 for r in results if r is True)
            total_time = end_time - start_time
            avg_time = total_time / len(tasks)
            
            # Asserts escalables según carga
            min_success_rate = max(0.6, 1.0 - (load_level * 0.02))  # Menor tasa con más carga
            max_avg_time = min(3.0, 0.2 + (load_level * 0.1))  # Más tiempo con más carga
            
            assert successful >= len(tasks) * min_success_rate, f"Tasa de éxito insuficiente para carga {load_level}"
            assert avg_time <= max_avg_time, f"Tiempo promedio excesivo para carga {load_level}: {avg_time:.3f}s"
            
            print(f"📊 Carga {load_level}: {successful}/{len(tasks)} exitosas, {avg_time:.3f}s promedio")
    
    async def test_grpc_peer_client_integration(self, endpoints, wait_for_services):
        """Test integración con PeerGrpcClient en nueva arquitectura"""
        await wait_for_services()
        
        # Importar desde nueva estructura
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        
        try:
            from peer.clients.grpc.peer_client import PeerGrpcClient
            
            grpc_client = PeerGrpcClient()
            
            # Test ping a múltiples peers concurrentemente
            ping_tasks = []
            peer_ips = ["localhost"] * 4
            peer_ports = [50071, 50072, 50073, 50074]  # Puertos de listado
            
            for ip, port in zip(peer_ips, peer_ports):
                task = grpc_client.ping_peer(ip, port, timeout=3)
                ping_tasks.append(task)
            
            start_time = time.time()
            ping_results = await asyncio.gather(*ping_tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_pings = sum(1 for r in ping_results if r is True)
            total_time = end_time - start_time
            
            # Asserts para pings concurrentes
            assert total_time < 10, f"Pings muy lentos: {total_time:.2f}s"
            # Al menos 1 peer debería responder
            assert successful_pings >= 1, f"Ningún peer responde a ping"
            
            print(f"🏓 Pings concurrentes: {successful_pings}/{len(ping_tasks)} peers responden")
            
        except ImportError as e:
            pytest.skip(f"No se puede importar PeerGrpcClient: {e}")
    
    @pytest.mark.slow
    async def test_sustained_load_new_arch(self, endpoints, wait_for_services):
        """Test carga sostenida con nueva arquitectura"""
        await wait_for_services()
        
        peer_url = endpoints["peers"][0]
        duration_seconds = 20  # 20 segundos de carga
        requests_per_second = 3
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            all_results = []
            
            while time.time() - start_time < duration_seconds:
                # Hacer requests_per_second requests variados
                batch_tasks = []
                
                for i in range(requests_per_second):
                    if i % 3 == 0:
                        task = self._test_status_operation(session, peer_url, f"sustained_{int(time.time())}_{i}")
                    elif i % 3 == 1:
                        task = self._test_local_files_operation(session, peer_url, f"sustained_{int(time.time())}_{i}")
                    else:
                        task = self._test_peers_list_operation(session, peer_url, f"sustained_{int(time.time())}_{i}")
                    
                    batch_tasks.append(task)
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                all_results.extend(batch_results)
                
                # Esperar hasta el siguiente segundo
                await asyncio.sleep(1)
            
            total_time = time.time() - start_time
            successful = sum(1 for r in all_results if r is True)
            total_requests = len(all_results)
            
            # Asserts para carga sostenida
            assert successful >= total_requests * 0.7, f"Tasa de éxito insuficiente en carga sostenida"
            assert total_requests >= duration_seconds * requests_per_second * 0.8, "Muy pocos requests ejecutados"
            
            success_rate = successful / total_requests if total_requests > 0 else 0
            actual_rps = total_requests / total_time
            
            print(f"⚡ Carga sostenida: {successful}/{total_requests} exitosos")
            print(f"📈 Tasa de éxito: {success_rate:.1%}, RPS real: {actual_rps:.2f}")
            
            assert success_rate >= 0.7, f"Tasa de éxito muy baja: {success_rate:.1%}"
            assert actual_rps >= requests_per_second * 0.8, f"RPS muy bajo: {actual_rps:.2f}"
    
    # Métodos auxiliares actualizados para nueva arquitectura
    
    async def _test_status_operation(self, session: aiohttp.ClientSession, peer_url: str, op_id: str) -> bool:
        """Test operación de status con nueva arquitectura"""
        try:
            async with session.get(f"{peer_url}/status", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    # Verificar estructura esperada de nueva arquitectura
                    required_fields = ["peer_name", "is_registered", "directory_server"]
                    for field in required_fields:
                        assert field in data, f"Campo {field} faltante en status"
                    return True
                return False
        except Exception:
            return False
    
    async def _test_local_files_operation(self, session: aiohttp.ClientSession, peer_url: str, op_id: str) -> bool:
        """Test operación de archivos locales"""
        try:
            async with session.get(f"{peer_url}/files/local", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    # Verificar estructura
                    assert "files" in data
                    assert "total" in data
                    assert isinstance(data["files"], list)
                    assert isinstance(data["total"], int)
                    return True
                return False
        except Exception:
            return False
    
    async def _test_peers_list_operation(self, session: aiohttp.ClientSession, peer_url: str, op_id: str) -> bool:
        """Test operación de lista de peers"""
        try:
            async with session.get(f"{peer_url}/peers", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    # Verificar estructura
                    assert "peers" in data or "total" in data
                    return True
                return False
        except Exception:
            return False
    
    async def _test_file_search_operation(self, session: aiohttp.ClientSession, peer_url: str, peer_name: str, filename: str) -> bool:
        """Test operación de búsqueda de archivos"""
        try:
            params = {"filename": filename}
            async with session.get(f"{peer_url}/files/search", params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    # Verificar estructura de respuesta
                    assert "filename" in data
                    assert "total_peers" in data or "peers" in data
                    assert data["filename"] == filename
                    return True
                return False
        except Exception:
            return False
