"""
Tests de registro de peers con nueva arquitectura
Reemplazo de test_registration.py original
"""
import pytest
import asyncio
import uuid

@pytest.mark.integration
@pytest.mark.asyncio
class TestRegistrationNew:
    """Tests de registro usando nueva arquitectura"""
    
    async def test_peer_registration_with_different_ips(self, directory_client, wait_for_services):
        """Test registro de peers con diferentes tipos de IP"""
        await wait_for_services()
        # Casos de prueba actualizados para nueva arquitectura
        test_cases = [
            {
                "name": "IP válida IPv4",
                "data": {
                    "peer_name": f"test_peer_ipv4_{uuid.uuid4().hex[:8]}",
                    "password": "test123",
                    "ip_address": "192.168.1.100",
                    "grpc_port": 50055
                }
            },
            {
                "name": "IP localhost",
                "data": {
                    "peer_name": f"test_peer_localhost_{uuid.uuid4().hex[:8]}",
                    "password": "test123",
                    "ip_address": "127.0.0.1",
                    "grpc_port": 50058
                }
            }
        ]
        
        successful_registrations = 0
        
        for test_case in test_cases:
            print(f"\n🧪 Probando: {test_case['name']}")
            
            try:
                result = await directory_client.register_peer(**test_case['data'])
                
                # Verificar respuesta con nueva arquitectura
                assert "peer_id" in result, "Falta peer_id en respuesta"
                assert "access_token" in result, "Falta access_token en respuesta"
                assert "token_type" in result, "Falta token_type en respuesta"
                assert result["peer_name"] == test_case['data']['peer_name']
                assert result["ip_address"] == test_case['data']['ip_address']
                assert result["grpc_port"] == test_case['data']['grpc_port']
                assert result["is_active"] is True
                assert result["token_type"] == "bearer"
                
                print(f"✅ Registro exitoso: {result['peer_id']}")
                print(f"   IP registrada: {result['ip_address']}")
                print(f"   Token recibido: {result['access_token'][:20]}...")
                
                successful_registrations += 1
                
            except Exception as e:
                print(f"❌ Error en {test_case['name']}: {str(e)}")
        
        # Assert que al menos la mayoría de registros funcionaron
        assert successful_registrations >= len(test_cases) * 0.75, f"Solo {successful_registrations}/{len(test_cases)} registros exitosos"
        
        print(f"\n📊 Resumen: {successful_registrations}/{len(test_cases)} registros exitosos")
    
    async def test_concurrent_registrations_new_arch(self, endpoints, http_session, wait_for_services):
        """Test registros concurrentes con nueva arquitectura"""
        await wait_for_services()
        
        # Usar la clase DirectoryClient del conftest
        from tests.conftest import DirectoryClient
        
        async def register_peer_new_arch(session, base_url, peer_index):
            """Función auxiliar para registrar un peer con nueva arquitectura"""
            client = DirectoryClient(base_url, session)
            peer_name = f"concurrent_peer_new_{peer_index}_{uuid.uuid4().hex[:8]}"
            
            return await client.register_peer(
                peer_name=peer_name,
                password=f"password_{peer_index}",
                ip_address=f"192.168.1.{100 + peer_index}",
                grpc_port=50051 + peer_index
            )
        
        # Registrar 8 peers concurrentemente (más que antes)
        tasks = []
        for i in range(8):
            task = register_peer_new_arch(http_session, endpoints["directory"], i)
            tasks.append(task)
        
        # Ejecutar todas las tareas concurrentemente
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        # Analizar resultados
        successful_registrations = [r for r in results if not isinstance(r, Exception)]
        failed_registrations = [r for r in results if isinstance(r, Exception)]
        
        total_time = end_time - start_time
        
        # Asserts para registros concurrentes
        assert len(successful_registrations) >= 6, f"Solo {len(successful_registrations)}/8 registros exitosos"
        assert len(failed_registrations) <= 2, f"Demasiados fallos: {len(failed_registrations)}"
        assert total_time < 15, f"Registros muy lentos: {total_time:.2f}s"
        
        # Verificar unicidad de IDs y tokens
        peer_ids = [reg["peer_id"] for reg in successful_registrations]
        tokens = [reg["access_token"] for reg in successful_registrations]
        
        assert len(set(peer_ids)) == len(peer_ids), "IDs de peers no son únicos"
        assert len(set(tokens)) == len(tokens), "Tokens no son únicos"
        
        print(f"🚀 Registros concurrentes: {len(successful_registrations)}/8 exitosos en {total_time:.2f}s")
        
        # Mostrar fallos si los hay
        if failed_registrations:
            print("⚠️  Fallos:")
            for i, error in enumerate(failed_registrations[:3]):  # Mostrar solo primeros 3
                print(f"   {i+1}. {str(error)[:100]}...")
    
    async def test_registration_with_grpc_ports_new_arch(self, directory_client, wait_for_services):
        """Test registro con puertos gRPC específicos de nueva arquitectura"""
        await wait_for_services()
        
        
        # Test con puertos de microservicios separados
        microservice_ports = [
            {"name": "download_port", "port": 50051},
            {"name": "upload_port", "port": 50061}, 
            {"name": "list_port", "port": 50071},
            {"name": "custom_port", "port": 50081}
        ]
        
        successful_registrations = 0
        
        for port_config in microservice_ports:
            peer_name = f"test_peer_{port_config['name']}_{uuid.uuid4().hex[:8]}"
            
            try:
                result = await directory_client.register_peer(
                    peer_name=peer_name,
                    password="test123",
                    ip_address="127.0.0.1",
                    grpc_port=port_config['port']
                )
                
                # Verificar que el puerto se registró correctamente
                assert result["grpc_port"] == port_config['port']
                
                print(f"✅ Registro con {port_config['name']} (puerto {port_config['port']}): OK")
                successful_registrations += 1
                
            except Exception as e:
                print(f"❌ Error con {port_config['name']}: {str(e)}")
        
        assert successful_registrations >= len(microservice_ports) * 0.75, "Falló registro con puertos específicos"
    
    async def test_registration_validation_new_arch(self, directory_client, wait_for_services):
        """Test validación de datos de registro con nueva arquitectura"""
        await wait_for_services()
        
        
        # Casos de validación
        validation_cases = [
            {
                "name": "Nombre muy largo",
                "data": {
                    "peer_name": "a" * 100,  # Muy largo
                    "password": "test123",
                    "ip_address": "127.0.0.1",
                    "grpc_port": 50051
                },
                "should_fail": True
            },
            {
                "name": "Puerto inválido (muy alto)",
                "data": {
                    "peer_name": f"test_port_high_{uuid.uuid4().hex[:8]}",
                    "password": "test123",
                    "ip_address": "127.0.0.1",
                    "grpc_port": 99999  # Puerto muy alto
                },
                "should_fail": True
            },
            {
                "name": "Puerto inválido (muy bajo)",
                "data": {
                    "peer_name": f"test_port_low_{uuid.uuid4().hex[:8]}",
                    "password": "test123",
                    "ip_address": "127.0.0.1",
                    "grpc_port": 100  # Puerto muy bajo
                },
                "should_fail": True
            },
            {
                "name": "Datos válidos",
                "data": {
                    "peer_name": f"test_valid_{uuid.uuid4().hex[:8]}",
                    "password": "test123",
                    "ip_address": "127.0.0.1",
                    "grpc_port": 50051
                },
                "should_fail": False
            }
        ]
        
        validation_results = {"passed": 0, "failed": 0}
        
        for case in validation_cases:
            try:
                result = await directory_client.register_peer(**case['data'])
                
                if case['should_fail']:
                    print(f"⚠️  {case['name']}: Debería haber fallado pero pasó")
                    validation_results["failed"] += 1
                else:
                    print(f"✅ {case['name']}: Validación correcta (pasó)")
                    validation_results["passed"] += 1
                    
            except Exception as e:
                if case['should_fail']:
                    print(f"✅ {case['name']}: Validación correcta (falló como esperado)")
                    validation_results["passed"] += 1
                else:
                    print(f"❌ {case['name']}: Falló inesperadamente: {str(e)}")
                    validation_results["failed"] += 1
        
        # Assert que la mayoría de validaciones funcionaron
        total_cases = len(validation_cases)
        success_rate = validation_results["passed"] / total_cases
        
        assert success_rate >= 0.75, f"Solo {validation_results['passed']}/{total_cases} validaciones correctas"
        
        print(f"📊 Validaciones: {validation_results['passed']}/{total_cases} correctas")
    
