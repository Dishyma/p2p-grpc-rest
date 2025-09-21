import asyncio
import aiohttp
import logging
import uuid
from typing import Dict, Any, List, Optional

from ..config import config

logger = logging.getLogger(__name__)

class DirectoryClient:
    """Cliente para comunicarse con el Directory Server"""

    def __init__(self):
        self.base_url = config.directory_server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        # Cargar token actual desde config al crear la sesión
        self._access_token = config.get_directory_access_token()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Inicia sesión contra el directory server y guarda el token en config."""
        try:
            url = f"{self.base_url}/auth/login"
            payload = {
                "username": username or config.directory_username,
                "password": password or config.directory_password,
            }
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("access_token")
                    if token:
                        self._access_token = token
                        config.set_directory_access_token(token)
                        logger.info("Login al directory server exitoso")
                        return True
                    logger.error("Respuesta de login sin access_token")
                    return False
                else:
                    detail = await response.text()
                    logger.error(f"Error en login: {response.status} - {detail}")
                    return False
        except Exception as e:
            logger.error(f"Excepción en login: {e}")
            return False

    def _auth_headers(self) -> Dict[str, str]:
        token = self._access_token or config.get_directory_access_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def validate_token(self) -> Optional[Dict[str, Any]]:
        """Valida el token actual contra el directory server."""
        try:
            url = f"{self.base_url}/auth/validate"
            headers = self._auth_headers()
            if not headers:
                logger.warning("No hay token para validar.")
                return None

            async with self.session.post(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Token validado exitosamente para: {data.get('peer_name')}")
                    return data
                else:
                    logger.warning(f"La validación del token falló. Status: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error validando token: {str(e)}")
            return None

    async def logout(self) -> bool:
        """Informa al directory server que el peer se está desconectando."""
        try:
            url = f"{self.base_url}/peers/logout"
            headers = self._auth_headers()
            if not headers:
                logger.warning("No hay sesión activa para cerrar.")
                return False

            async with self.session.post(url, headers=headers) as response:
                if response.status == 200:
                    logger.info("Logout exitoso en el directory server.")
                    return True
                else:
                    logger.error(f"Error en el logout: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Excepción durante el logout: {str(e)}")
            return False

    async def register_peer(self, peer_name: str, password: str, ip_address: str, grpc_port: int) -> Optional[Dict[str, Any]]:
        """Registrar el peer con credenciales y devolver info completa incluyendo token."""
        try:
            logger.info(f"[LOG] Intentando registrar peer: {peer_name} en {ip_address}:{grpc_port}")
            url = f"{self.base_url}/peers/register"
            payload = {
                "peer_name": peer_name,
                "password": password,
                "ip_address": ip_address, 
                "grpc_port": grpc_port
            }
            logger.info(f"[NETWORK] Enviando POST a {url} con peer_name: {peer_name}")

            async with self.session.post(url, json=payload) as response:
                logger.info(f"[NETWORK] Respuesta del servidor: Status {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"[NETWORK] Respuesta JSON: {data}")
                    peer_id = data.get("peer_id")
                    access_token = data.get("access_token")
                    
                    if peer_id and access_token:
                        # Guardar el token automáticamente
                        self._access_token = access_token
                        config.set_directory_access_token(access_token)
                        logger.info(f"[SUCCESS] Peer registrado exitosamente con ID: {peer_id} y token guardado")
                        return data  # Devolver toda la respuesta
                    else:
                        logger.error("[ERROR] La respuesta de registro no contenía peer_id o access_token")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"[ERROR] Error registrando peer: {response.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"[ERROR] Error en registro: {str(e)}")
            return None

    async def send_heartbeat(self, peer_id: str) -> bool:
        """Enviar heartbeat al directory server"""
        try:
            url = f"{self.base_url}/peers/heartbeat"
            # Convertir string a UUID string para el servidor
            payload = {"peer_id": str(uuid.UUID(peer_id))}
            async with self.session.post(url, json=payload, headers=self._auth_headers()) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error enviando heartbeat: {str(e)}")
            return False

    async def get_peer_files(self, filename: str) -> List[Dict[str, Any]]:
        """Obtener información de peers que tienen un archivo específico"""
        try:
            url = f"{self.base_url}/peers/files/search"
            params = {"filename": filename}
            async with self.session.get(url, params=params, headers=self._auth_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    # La API devuelve un objeto con clave 'files'
                    if isinstance(data, dict):
                        return data.get("files", [])
                    return []
                else:
                    logger.error(f"Error buscando archivo: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error buscando archivo: {str(e)}")
            return []

    async def announce_files(self, peer_id: str, files: List[Dict[str, Any]]) -> bool:
        """Anunciar archivos disponibles al directory server"""
        try:
            url = f"{self.base_url}/peers/files/announce"
            # Convertir string a UUID string para el servidor
            payload = {"peer_id": str(uuid.UUID(peer_id)), "files": files}
            async with self.session.post(url, json=payload, headers=self._auth_headers()) as response:
                if response.status == 200:
                    logger.info(f"Archivos anunciados exitosamente: {len(files)} archivos")
                    return True
                else:
                    try:
                        detail = await response.text()
                    except Exception:
                        detail = "<no-body>"
                    logger.error(f"Error anunciando archivos: {response.status} - {detail}")
                    return False
        except Exception as e:
            logger.error(f"Error anunciando archivos: {str(e)}")
            return False

    async def get_active_peers(self) -> List[Dict[str, Any]]:
        """Obtener lista de peers activos"""
        try:
            url = f"{self.base_url}/peers"
            async with self.session.get(url, headers=self._auth_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    # La API puede devolver una lista directa o un objeto con clave 'peers'
                    if isinstance(data, list):
                        return data
                    return data.get("peers", [])
                else:
                    logger.error(f"Error obteniendo peers: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error obteniendo peers: {str(e)}")
            return []

    async def get_peer_files_list(self, peer_id: str) -> List[Dict[str, Any]]:
        """Obtener la lista de archivos que el servidor cree que tiene este peer"""
        try:
            url = f"{self.base_url}/peers/{peer_id}/files"
            async with self.session.get(url, headers=self._auth_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("files", [])
                else:
                    logger.warning(f"No se pudo obtener lista de archivos del peer: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error obteniendo archivos del peer: {str(e)}")
            return []

    async def remove_peer_file(self, peer_id: str, filename: str) -> bool:
        """Eliminar un archivo específico del registro del peer"""
        try:
            url = f"{self.base_url}/peers/{peer_id}/files/{filename}"
            async with self.session.delete(url, headers=self._auth_headers()) as response:
                if response.status == 200:
                    logger.debug(f"Archivo '{filename}' eliminado del registro")
                    return True
                else:
                    logger.warning(f"No se pudo eliminar archivo '{filename}': {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error eliminando archivo '{filename}': {str(e)}")
            return False

