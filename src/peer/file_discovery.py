import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import aiofiles
import grpc
from .config import config
from .rest_client.directory_client import DirectoryClient
# Removed PeerManager import to avoid circular dependencies
from generated import file_service_pb2
from generated import file_service_pb2_grpc

logger = logging.getLogger(__name__)

class FileDiscoveryService:
    """Servicio para descubrir y descargar archivos P2P"""

    def __init__(self, peer_manager=None):
        self.peer_manager = peer_manager

    async def find_file(self, filename: str) -> List[Dict[str, Any]]:
        """Buscar un archivo en la red P2P"""
        logger.info(f"[SEARCH] Buscando archivo: {filename}")

        async with DirectoryClient() as client:
            peers = await client.get_peer_files(filename)

        if not peers:
            logger.warning(f"[FILE] Archivo '{filename}' no encontrado en la red")
            return []

        logger.info(f"[SUCCESS] Archivo '{filename}' encontrado en {len(peers)} peer(s)")
        return peers

    async def download_file(self, filename: str, preferred_peer_id: Optional[str] = None) -> bool:
        """Descargar un archivo desde la red P2P con failover"""
        # Buscar archivo en directory server
        peers_with_file = await self.find_file(filename)
        
        # Intentar descarga desde peers del directory
        if peers_with_file:
            # Seleccionar peer (preferido o el primero disponible)
            target_peer: Dict[str, Any]
            if preferred_peer_id:
                target_peer = next((p for p in peers_with_file if p.get('id') == preferred_peer_id), None)
                if not target_peer:
                    logger.warning(f"Peer preferido {preferred_peer_id} no posee el archivo. Usando el primero disponible.")
                    target_peer = peers_with_file[0]
            else:
                target_peer = peers_with_file[0]

            logger.info(f"[DOWNLOAD] Descargando '{filename}' desde {target_peer.get('id')}")
            
            # Intentar descarga con reintentos
            success = await self._download_with_retry(filename, target_peer)
            if success:
                await self._announce_downloaded_file(filename)
                return True
            
            # Si falla el peer preferido, intentar con otros peers del directory
            for peer in peers_with_file[1:]:
                logger.info(f"[PROCESSING] Reintentando descarga desde {peer.get('id')}")
                success = await self._download_with_retry(filename, peer)
                if success:
                    await self._announce_downloaded_file(filename)
                    return True

        # Si fallan todos los peers del directory, intentar peers amigos (failover)
        logger.warning(f"[FILE] Archivo '{filename}' no encontrado o falló descarga desde directory. Intentando peers amigos...")
        success = await self._try_friend_peers(filename)
        if success:
            await self._announce_downloaded_file(filename)
            return True

        logger.error(f"[ERROR] Error descargando '{filename}' desde todos los peers disponibles")
        return False

    async def _download_from_peer(self, filename: str, peer: Dict[str, Any]) -> bool:
        """Descargar archivo desde un peer específico"""
        peer_id = peer.get('id')
        peer_ip = peer.get('ip_address')
        # Usar puerto de descarga específico
        peer_port = peer.get('grpc_download_port', peer.get('grpc_port', 50051))

        if not all([peer_id, peer_ip, peer_port]):
            logger.error("Información incompleta del peer")
            return False

        try:
            # Crear canal gRPC con timeout
            channel = grpc.aio.insecure_channel(f"{peer_ip}:{peer_port}")
            await channel.channel_ready()

            # Crear stub
            stub = file_service_pb2_grpc.FileTransferStub(channel)

            # Solicitar descarga
            request = file_service_pb2.DownloadRequest(filename=filename)
            downloaded_size = 0
            chunks_count = 0

            # Crear directorio de destino si no existe
            from pathlib import Path
            Path(config.files_directory).mkdir(parents=True, exist_ok=True)

            # Descargar archivo
            output_path = Path(config.files_directory) / filename
            async with aiofiles.open(output_path, 'wb') as output_file:
                async for chunk in stub.DownloadFile(request):
                    if not chunk.content:
                        break

                    await output_file.write(chunk.content)
                    downloaded_size += len(chunk.content)
                    chunks_count += 1

                    # Mostrar progreso cada 10 chunks
                    if chunks_count % 10 == 0:
                        print(f"[DOWNLOAD] {chunks_count} chunks ({downloaded_size / 1024:.1f} KB)")

            await channel.close()

            # Verificar integridad si hay hash disponible
            if peer.get('file_hash'):
                import hashlib
                actual_hash = self._calculate_file_hash(output_path)
                if actual_hash == peer.get('file_hash'):
                    logger.info("[SUCCESS] Hash verificado correctamente")
                else:
                    logger.warning("[WARNING] Hash mismatch detectado")

            return True

        except asyncio.TimeoutError:
            logger.error(f"Timeout conectando a {peer_id}")
            return False
        except Exception as e:
            logger.error(f"Error descargando desde {peer_id}: {str(e)}")
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcular hash SHA256 de un archivo"""
        import hashlib

        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as file:
            while True:
                chunk = file.read(8192)
                if not chunk:
                    break
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    async def _download_with_retry(self, filename: str, peer: Dict[str, Any], max_retries: int = 3) -> bool:
        """Descargar archivo con reintentos y backoff exponencial"""
        for attempt in range(max_retries):
            try:
                success = await self._download_from_peer(filename, peer)
                if success:
                    return True
            except Exception as e:
                logger.warning(f"Intento {attempt + 1}/{max_retries} falló: {str(e)}")
            
            if attempt < max_retries - 1:  # No esperar en el último intento
                wait_time = 0.5 * (2 ** attempt)  # Backoff exponencial: 0.5s, 1s, 2s
                logger.info(f"[WAITING] Esperando {wait_time}s antes del siguiente intento...")
                await asyncio.sleep(wait_time)
        
        return False

    async def _try_friend_peers(self, filename: str) -> bool:
        """Intentar descarga desde peers amigos configurados"""
        friend_endpoints = []
        
        # Construir lista de endpoints de friends
        if config.peer_friend_primary_grpc:
            friend_endpoints.append(config.peer_friend_primary_grpc)
        if config.peer_friend_backup_grpc:
            friend_endpoints.append(config.peer_friend_backup_grpc)
        
        if not friend_endpoints:
            logger.warning("No hay peers amigos configurados para failover")
            return False
        
        logger.info(f"[PROCESSING] Intentando descarga desde {len(friend_endpoints)} peer(s) amigo(s)")
        
        for endpoint in friend_endpoints:
            logger.info(f"[DOWNLOAD] Intentando descarga desde peer amigo: {endpoint}")
            success = await self._download_from_endpoint(filename, endpoint)
            if success:
                logger.info(f"[SUCCESS] Descarga exitosa desde peer amigo: {endpoint}")
                return True
        
        return False

    async def _download_from_endpoint(self, filename: str, endpoint: str) -> bool:
        """Descargar archivo desde un endpoint gRPC específico (host:puerto)"""
        try:
            # Crear canal gRPC con timeout
            channel = grpc.aio.insecure_channel(
                endpoint,
                options=[
                    ('grpc.keepalive_time_ms', 20000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.max_receive_message_length', 64 * 1024 * 1024),  # 64MB
                ]
            )
            
            # Esperar conexión con timeout
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)

            # Crear stub
            stub = file_service_pb2_grpc.FileTransferStub(channel)

            # Solicitar descarga
            request = file_service_pb2.DownloadRequest(filename=filename)
            downloaded_size = 0
            chunks_count = 0

            # Crear directorio de destino si no existe
            Path(config.files_directory).mkdir(parents=True, exist_ok=True)

            # Descargar archivo
            output_path = Path(config.files_directory) / filename
            async with aiofiles.open(output_path, 'wb') as output_file:
                async for chunk in stub.DownloadFile(request):
                    if not chunk.content:
                        break

                    await output_file.write(chunk.content)
                    downloaded_size += len(chunk.content)
                    chunks_count += 1

                    # Mostrar progreso cada 10 chunks
                    if chunks_count % 10 == 0:
                        logger.debug(f"[DOWNLOAD] {chunks_count} chunks ({downloaded_size / 1024:.1f} KB)")

            await channel.close()
            
            if downloaded_size > 0:
                logger.info(f"[SUCCESS] Descarga completada desde {endpoint}: {downloaded_size} bytes")
                return True
            else:
                logger.warning(f"[WARNING] Archivo vacío o no encontrado en {endpoint}")
                return False

        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] Timeout conectando a {endpoint}")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Error descargando desde {endpoint}: {str(e)}")
            return False

    async def _announce_downloaded_file(self, filename: str):
        """Anunciar archivo descargado al directory server si hay peer_manager"""
        if self.peer_manager:
            try:
                output_path = Path(config.files_directory) / filename
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    file_hash = self._calculate_file_hash(output_path)
                    await self.peer_manager.announce_new_file(filename, file_size, file_hash)
                    logger.info(f"[ANNOUNCE] Archivo '{filename}' anunciado al directory server")
            except Exception as e:
                logger.warning(f"[WARNING] Error anunciando archivo '{filename}': {str(e)}")

    async def list_available_files(self, peer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Listar archivos disponibles en la red"""
        async with DirectoryClient() as client:
            peers = await client.get_active_peers()

        all_files = []
        seen_files = set()

        for peer in peers:
            if peer_id and peer.get('id') != peer_id:
                continue

            try:
                # Obtener archivos del peer via gRPC
                files = await self._get_peer_files(peer)
                for file_info in files:
                    file_key = (file_info.get('filename'), file_info.get('file_hash'))
                    if file_key not in seen_files:
                        seen_files.add(file_key)
                        all_files.append({
                            **file_info,
                            'available_in': [peer.get('id')]
                        })
                    else:
                        # Agregar peer a la lista de peers con el archivo
                        existing_file = next(f for f in all_files
                                           if (f.get('filename'), f.get('file_hash')) == file_key)
                        existing_file['available_in'].append(peer.get('id'))

            except Exception as e:
                logger.debug(f"Error obteniendo archivos de {peer.get('id')}: {str(e)}")

        return all_files

    async def _get_peer_files(self, peer: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtener lista de archivos de un peer específico via gRPC"""
        peer_id = peer.get('id')
        peer_ip = peer.get('ip_address')
        # Usar puerto de listado específico
        peer_port = peer.get('grpc_list_port', peer.get('grpc_port', 50071))

        try:
            channel = grpc.aio.insecure_channel(f"{peer_ip}:{peer_port}")
            await channel.channel_ready()

            stub = file_service_pb2_grpc.FileTransferStub(channel)

            request = file_service_pb2.ListFilesRequest()
            response = await stub.ListFiles(request)

            await channel.close()
            return [{
                'filename': file_info.filename,
                'file_size': file_info.file_size,
                'file_hash': file_info.file_hash
            } for file_info in response.files]

        except Exception:
            return []
