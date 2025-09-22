"""
Configuración global de pytest para el sistema P2P
"""
import os
import json
import asyncio
import pytest
import pytest_asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any
import time

# Configuración de endpoints por entorno
DEFAULT_ENDPOINTS = {
    "directory": "http://localhost:8080/api/v1",
    "peers": [
        "http://localhost:8001",
        "http://localhost:8002", 
        "http://localhost:8003",
        "http://localhost:8004"
    ]
}

@pytest.fixture(scope="session")
def endpoints() -> Dict[str, Any]:
    """
    Fixture que proporciona endpoints según el entorno.
    
    Para local: usa localhost
    Para AWS: lee de terraform outputs.json
    """
    # Verificar si estamos en modo AWS
    terraform_outputs = Path("infra/terraform/outputs.json")
    
    if terraform_outputs.exists():
        # Modo AWS - leer endpoints de terraform
        with open(terraform_outputs) as f:
            outputs = json.load(f)
        
        # Extraer URLs de los outputs de terraform
        # Ajustar según la estructura real de tus outputs
        return {
            "directory": outputs.get("directory_server_url", {}).get("value", DEFAULT_ENDPOINTS["directory"]),
            "peers": outputs.get("peer_urls", {}).get("value", DEFAULT_ENDPOINTS["peers"])
        }
    else:
        # Modo local - usar endpoints por defecto
        return DEFAULT_ENDPOINTS

@pytest_asyncio.fixture(scope="function")
async def http_session():
    """Sesión HTTP reutilizable para todos los tests"""
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        yield session

@pytest.fixture(scope="session")
def event_loop():
    """Event loop para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def wait_for_services(endpoints):
    """
    Devuelve una función async que espera a que los servicios estén disponibles
    """
    async def _wait_for_services():
        """Función interna que hace la verificación real"""
        async def check_service(url: str, max_retries: int = 10) -> bool:
            """Verifica si un servicio está disponible"""
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        # Para directory server, usar endpoint de health
                        if "8080" in url:
                            check_url = f"{url}/health"
                        else:
                            # Para peers, usar endpoint de status
                            check_url = f"{url}/status"
                        
                        async with session.get(check_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status == 200:
                                return True
                except Exception:
                    pass
                
                await asyncio.sleep(1)
            
            return False
        
        # Verificar directory server
        directory_ready = await check_service(endpoints["directory"])
        if not directory_ready:
            pytest.skip(f"Directory server no disponible: {endpoints['directory']}")
        
        # Verificar al menos 1 peer
        peers_ready = 0
        for peer_url in endpoints["peers"][:2]:  # Solo verificar los primeros 2
            if await check_service(peer_url):
                peers_ready += 1
        
        if peers_ready < 1:
            pytest.skip(f"Ningún peer disponible. Encontrados: {peers_ready}")
        
        return True
    
    return _wait_for_services

class DirectoryClient:
    """Cliente para interactuar con el directory server"""
    
    def __init__(self, base_url: str, session: aiohttp.ClientSession):
        self.base_url = base_url
        self.session = session
        self.access_token = None
    
    async def register_peer(self, peer_name: str, password: str, ip_address: str = "127.0.0.1", grpc_port: int = 50051):
        """Registra un peer y obtiene el token"""
        data = {
            "peer_name": peer_name,
            "password": password,
            "ip_address": ip_address,
            "grpc_port": grpc_port
        }
        
        async with self.session.post(f"{self.base_url}/peers/register", json=data) as response:
            if response.status == 200:
                result = await response.json()
                self.access_token = result.get("access_token")
                return result
            else:
                text = await response.text()
                raise Exception(f"Registration failed: {response.status} - {text}")
    
    async def login(self, username: str, password: str):
        """Login y obtener token"""
        data = {"username": username, "password": password}
        
        async with self.session.post(f"{self.base_url}/auth/login", json=data) as response:
            if response.status == 200:
                result = await response.json()
                self.access_token = result.get("access_token")
                return result
            else:
                text = await response.text()
                raise Exception(f"Login failed: {response.status} - {text}")
    
    async def get_active_peers(self):
        """Obtiene peers activos (requiere token)"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        async with self.session.get(f"{self.base_url}/peers", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Get peers failed: {response.status} - {text}")
    
    async def search_files(self, filename: str):
        """Busca archivos (requiere token)"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        params = {"filename": filename}
        async with self.session.get(f"{self.base_url}/peers/files/search", params=params, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Search files failed: {response.status} - {text}")

@pytest_asyncio.fixture
async def directory_client(endpoints, http_session):
    """Fixture que devuelve una instancia de DirectoryClient"""
    return DirectoryClient(endpoints["directory"], http_session)

class PeerClient:
    """Cliente para interactuar con peers"""
    
    def __init__(self, peer_urls: List[str], session: aiohttp.ClientSession):
        self.peer_urls = peer_urls
        self.session = session
    
    async def get_status(self, peer_index: int = 0):
        """Obtiene status de un peer"""
        url = self.peer_urls[peer_index]
        async with self.session.get(f"{url}/status") as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Get status failed: {response.status} - {text}")
    
    async def list_local_files(self, peer_index: int = 0):
        """Lista archivos locales de un peer"""
        url = self.peer_urls[peer_index]
        async with self.session.get(f"{url}/files/local") as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"List files failed: {response.status} - {text}")
    
    async def search_files(self, filename: str, peer_index: int = 0):
        """Busca archivos desde un peer"""
        url = self.peer_urls[peer_index]
        params = {"filename": filename}
        async with self.session.get(f"{url}/files/search", params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Search files failed: {response.status} - {text}")
    
    async def get_peers(self, peer_index: int = 0):
        """Obtiene lista de peers desde un peer"""
        url = self.peer_urls[peer_index]
        async with self.session.get(f"{url}/peers") as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Get peers failed: {response.status} - {text}")

@pytest_asyncio.fixture
async def peer_client(endpoints, http_session):
    """Fixture que devuelve una instancia de PeerClient"""
    return PeerClient(endpoints["peers"], http_session)

@pytest.fixture
def sample_files():
    """Archivos de muestra para tests"""
    return {
        "small_file.txt": b"Hello, P2P World!",
        "medium_file.txt": b"A" * 1024,  # 1KB
        "test_document.pdf": b"PDF_CONTENT_" + b"X" * 2048,  # ~2KB
    }

@pytest.fixture(scope="session")
def test_peer_credentials():
    """Credenciales de prueba para peers"""
    return [
        {"peer_name": "test_peer_1", "password": "test123"},
        {"peer_name": "test_peer_2", "password": "test456"},
        {"peer_name": "test_peer_3", "password": "test789"},
    ]

# Markers para skipear tests según condiciones
def pytest_configure(config):
    """Configuración adicional de pytest"""
    # Registrar markers personalizados
    config.addinivalue_line("markers", "unit: Tests unitarios")
    config.addinivalue_line("markers", "integration: Tests de integración")
    config.addinivalue_line("markers", "aws: Tests contra AWS")
    config.addinivalue_line("markers", "grpc: Tests de gRPC")
    config.addinivalue_line("markers", "slow: Tests lentos")
    config.addinivalue_line("markers", "concurrency: Tests de concurrencia")

def pytest_collection_modifyitems(config, items):
    """Modificar items de test según markers"""
    # Skip tests AWS si no hay outputs de terraform
    terraform_outputs = Path("infra/terraform/outputs.json")
    
    for item in items:
        # Marcar tests AWS para skip si no hay infraestructura
        if "aws" in item.keywords and not terraform_outputs.exists():
            item.add_marker(pytest.mark.skip(reason="No AWS infrastructure found"))
        
        # Marcar tests lentos
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.timeout(60))
