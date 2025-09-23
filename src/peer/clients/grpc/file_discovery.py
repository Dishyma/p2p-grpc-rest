"""
Servicio de descubrimiento y descarga de archivos P2P
Responsabilidad: Orquestación, lógica de negocio, failover
"""
import asyncio
import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path

from .peer_client import PeerGrpcClient
from ..rest.directory_client import DirectoryClient
from ...core.config import config

logger = logging.getLogger(__name__)

class FileDiscoveryService:
    """
    Servicio de alto nivel para descubrimiento y descarga de archivos P2P
    
    Responsabilidades:
    - Orquestar búsqueda en Directory Server
    - Coordinar descarga desde peers via gRPC
    - Implementar failover y reintentos
    - Anunciar archivos descargados
    """
    
    def __init__(self, peer_manager=None):
        self.peer_manager = peer_manager
        self.grpc_client = PeerGrpcClient()
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def find_file(self, filename: str) -> List[Dict[str, Any]]:
        """
        Busca un archivo en la red P2P
        
        Args:
            filename: Nombre del archivo a buscar
            
        Returns:
            List[Dict]: Lista de peers que tienen el archivo
        """
        try:
            async with DirectoryClient() as client:
                files_list = await client.search_files(filename)
                
                if files_list:
                    peers_with_file = []
                    for file_info in files_list:
                        peers_with_file.append({
                            'id': file_info.get('id'),
                            'ip_address': file_info.get('ip_address'),
                            'grpc_port': file_info.get('grpc_port'),
                            'grpc_download_port': file_info.get('grpc_port'),
                            'filename': file_info.get('filename'),
                            'file_size': file_info.get('file_size'),
                            'file_hash': file_info.get('file_hash')
                        })
                    
                    logger.info(f"[DISCOVERY] Archivo '{filename}' encontrado en {len(peers_with_file)} peers")
                    return peers_with_file
                else:
                    logger.info(f"[DISCOVERY] Archivo '{filename}' no encontrado en Directory Server")
                    return []
                    
        except Exception as e:
            logger.error(f"[DISCOVERY] Error buscando archivo '{filename}': {str(e)}")
            return []
    
    async def download_file(self, filename: str, preferred_peer_id: Optional[str] = None) -> bool:
        """
        Descarga un archivo desde la red P2P con failover
        
        Args:
            filename: Nombre del archivo a descargar
            preferred_peer_id: ID del peer preferido (opcional)
            
        Returns:
            bool: True si descarga exitosa, False si falla
        """
        logger.info(f"[DISCOVERY] Iniciando descarga de '{filename}'")
        
        peers_with_file = await self.find_file(filename)
        
        if peers_with_file:
            target_peer = None
            if preferred_peer_id:
                target_peer = next((p for p in peers_with_file if p.get('id') == preferred_peer_id), None)
            
            if not target_peer:
                target_peer = peers_with_file[0]
            
            logger.info(f"[DISCOVERY] Descargando '{filename}' desde peer {target_peer.get('id')}")
            
            success = await self._download_with_retry(filename, target_peer)
            if success:
                await self._announce_downloaded_file(filename)
                return True
            
            for peer in peers_with_file[1:]:
                logger.info(f"[DISCOVERY] Reintentando descarga desde peer {peer.get('id')}")
                success = await self._download_with_retry(filename, peer)
                if success:
                    await self._announce_downloaded_file(filename)
                    return True
        
        logger.warning(f"[DISCOVERY] Archivo '{filename}' no encontrado o falló descarga desde Directory. Intentando peers amigos...")
        success = await self._try_friend_peers(filename)
        if success:
            await self._announce_downloaded_file(filename)
            return True
        
        logger.error(f"[DISCOVERY] Falló descarga de '{filename}' desde todos los peers disponibles")
        return False
    
    async def _download_with_retry(self, filename: str, peer: Dict[str, Any]) -> bool:
        """Descarga archivo desde un peer específico con reintentos"""
        peer_id = peer.get('id')
        peer_ip = peer.get('ip_address')
        peer_port = peer.get('grpc_download_port', peer.get('grpc_port', 50051))
        
        if not all([peer_id, peer_ip, peer_port]):
            logger.error(f"[DISCOVERY] Información incompleta del peer: {peer}")
            return False
        
        output_path = Path(config.files_directory) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"[DISCOVERY] Intento {attempt + 1}/{self.max_retries} - Descargando desde {peer_ip}:{peer_port}")
                
                success = await self.grpc_client.download_file_from_peer(
                    peer_ip=peer_ip,
                    peer_port=peer_port,
                    filename=filename,
                    output_path=output_path,
                    timeout=30
                )
                
                if success:
                    if peer.get('file_hash'):
                        actual_hash = self._calculate_file_hash(output_path)
                        expected_hash = peer.get('file_hash')
                        
                        if actual_hash != expected_hash:
                            logger.error(f"[DISCOVERY] Hash mismatch para {filename}: esperado {expected_hash}, obtenido {actual_hash}")
                            output_path.unlink(missing_ok=True)  # Eliminar archivo corrupto
                            continue
                    
                    logger.info(f"[DISCOVERY] Descarga exitosa de '{filename}' desde {peer_id}")
                    return True
                
            except Exception as e:
                logger.warning(f"[DISCOVERY] Intento {attempt + 1}/{self.max_retries} falló: {str(e)}")
            
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.info(f"[DISCOVERY] Esperando {wait_time}s antes del siguiente intento...")
                await asyncio.sleep(wait_time)
        
        logger.error(f"[DISCOVERY] Falló descarga de '{filename}' desde {peer_id} después de {self.max_retries} intentos")
        return False
    
    async def _try_friend_peers(self, filename: str) -> bool:
        """Intentar descarga desde peers amigos configurados"""
        friend_endpoints = []
        
        if config.peer_friend_primary_grpc:
            friend_endpoints.append(config.peer_friend_primary_grpc)
        if config.peer_friend_backup_grpc:
            friend_endpoints.append(config.peer_friend_backup_grpc)
        
        if not friend_endpoints:
            logger.warning("[DISCOVERY] No hay peers amigos configurados para failover")
            return False
        
        for endpoint in friend_endpoints:
            logger.info(f"[DISCOVERY] Intentando descarga desde peer amigo: {endpoint}")
            success = await self._download_from_endpoint(filename, endpoint)
            if success:
                logger.info(f"[DISCOVERY] Descarga exitosa desde peer amigo: {endpoint}")
                return True
        
        logger.error("[DISCOVERY] Falló descarga desde todos los peers amigos")
        return False
    
    async def _download_from_endpoint(self, filename: str, endpoint: str) -> bool:
        """Descargar archivo desde un endpoint gRPC específico (host:puerto)"""
        try:
            if ':' in endpoint:
                peer_ip, peer_port = endpoint.split(':', 1)
                peer_port = int(peer_port)
            else:
                peer_ip = endpoint
                peer_port = 50051
            
            output_path = Path(config.files_directory) / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            success = await self.grpc_client.download_file_from_peer(
                peer_ip=peer_ip,
                peer_port=peer_port,
                filename=filename,
                output_path=output_path,
                timeout=30
            )
            
            return success
            
        except Exception as e:
            logger.error(f"[DISCOVERY] Error descargando desde {endpoint}: {str(e)}")
            return False
    
    async def _announce_downloaded_file(self, filename: str):
        """Anunciar archivo descargado al Directory Server"""
        try:
            if self.peer_manager:
                await self.peer_manager.announce_one_file_by_name(filename)
                logger.info(f"[DISCOVERY] Archivo '{filename}' anunciado al Directory Server")
        except Exception as e:
            logger.warning(f"[DISCOVERY] Error anunciando archivo '{filename}': {str(e)}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcular hash SHA256 de un archivo"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"[DISCOVERY] Error calculando hash de {file_path}: {str(e)}")
            return ""
    
    async def get_all_network_files(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los archivos disponibles en la red P2P
        
        Returns:
            List[Dict]: Lista de archivos con información de disponibilidad
        """
        try:
            async with DirectoryClient() as client:
                peers = await client.get_active_peers()
            
            if not peers:
                logger.warning("[DISCOVERY] No hay peers activos en la red")
                return []
            
            all_files = []
            seen_files = set()
            
            for peer in peers:
                if not peer.get('ip_address') or not peer.get('grpc_port'):
                    continue
                
                try:
                    list_port = peer.get('grpc_list_port', peer.get('grpc_port', 50071))
                    
                    files = await self.grpc_client.list_files_from_peer(
                        peer_ip=peer.get('ip_address'),
                        peer_port=list_port,
                        timeout=10
                    )
                    
                    for file_info in files:
                        file_key = (file_info.get('filename'), file_info.get('file_hash'))
                        if file_key not in seen_files:
                            seen_files.add(file_key)
                            all_files.append({
                                **file_info,
                                'available_in': [peer.get('id')]
                            })
                        else:
                            existing_file = next(f for f in all_files
                                               if (f.get('filename'), f.get('file_hash')) == file_key)
                            existing_file['available_in'].append(peer.get('id'))
                
                except Exception as e:
                    logger.debug(f"[DISCOVERY] Error obteniendo archivos de peer {peer.get('id')}: {str(e)}")
            
            logger.info(f"[DISCOVERY] Encontrados {len(all_files)} archivos únicos en la red")
            return all_files
            
        except Exception as e:
            logger.error(f"[DISCOVERY] Error obteniendo archivos de la red: {str(e)}")
            return []
    
    async def _get_peer_files(self, peer: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtener lista de archivos de un peer específico via gRPC"""
        peer_id = peer.get('id')
        peer_ip = peer.get('ip_address')
        peer_port = peer.get('grpc_list_port', peer.get('grpc_port', 50071))
        
        try:
            files = await self.grpc_client.list_files_from_peer(
                peer_ip=peer_ip,
                peer_port=peer_port,
                timeout=10
            )
            
            logger.debug(f"[DISCOVERY] Obtenidos {len(files)} archivos de peer {peer_id}")
            return files
            
        except Exception as e:
            logger.error(f"[DISCOVERY] Error obteniendo archivos de peer {peer_id}: {str(e)}")
            return []
