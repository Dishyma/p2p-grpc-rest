"""
Cliente gRPC puro para comunicación peer-to-peer
Responsabilidad: Solo comunicación gRPC, sin lógica de negocio
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import grpc
import aiofiles

from ...core.path_setup import setup_paths
setup_paths()
import file_service_pb2, file_service_pb2_grpc

logger = logging.getLogger(__name__)

class PeerGrpcClient:
    """Cliente gRPC puro para comunicación con otros peers"""
    
    def __init__(self):
        self.default_timeout = 30
        self.chunk_size = 64 * 1024
    
    async def download_file_from_peer(
        self, 
        peer_ip: str, 
        peer_port: int, 
        filename: str,
        output_path: Optional[Path] = None,
        timeout: int = None
    ) -> bool:
        """
        Descarga un archivo específico de un peer via gRPC
        
        Args:
            peer_ip: IP del peer
            peer_port: Puerto gRPC de descarga del peer
            filename: Nombre del archivo a descargar
            output_path: Ruta donde guardar (opcional)
            timeout: Timeout en segundos
            
        Returns:
            bool: True si descarga exitosa, False si falla
        """
        timeout = timeout or self.default_timeout
        
        try:
            channel = grpc.aio.insecure_channel(
                f"{peer_ip}:{peer_port}",
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.max_receive_message_length', 64 * 1024 * 1024),
                ]
            )
            
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            
            stub = file_service_pb2_grpc.FileTransferStub(channel)
            request = file_service_pb2.DownloadRequest(filename=filename)
            
            downloaded_size = 0
            chunks_count = 0
            
            if output_path:
                async with aiofiles.open(output_path, 'wb') as output_file:
                    async for chunk in stub.DownloadFile(request):
                        if not chunk.content:
                            break
                        
                        await output_file.write(chunk.content)
                        downloaded_size += len(chunk.content)
                        chunks_count += 1
                        
                        if chunks_count % 10 == 0:
                            logger.debug(f"[GRPC] Descargados {chunks_count} chunks ({downloaded_size / 1024:.1f} KB)")
            else:
                chunks = []
                async for chunk in stub.DownloadFile(request):
                    if not chunk.content:
                        break
                    
                    chunks.append(chunk.content)
                    downloaded_size += len(chunk.content)
                    chunks_count += 1
                
                if chunks:
                    file_data = b''.join(chunks)
                    return file_data
            
            await channel.close()
            
            logger.info(f"[GRPC] Descarga exitosa: {filename} ({downloaded_size} bytes, {chunks_count} chunks)")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"[GRPC] Timeout descargando {filename} desde {peer_ip}:{peer_port}")
            return False
        except grpc.RpcError as e:
            logger.error(f"[GRPC] Error RPC descargando {filename}: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            logger.error(f"[GRPC] Error inesperado descargando {filename}: {str(e)}")
            return False
    
    async def upload_file_to_peer(
        self,
        peer_ip: str,
        peer_port: int,
        filename: str,
        file_data: bytes,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Sube un archivo a un peer via gRPC
        
        Args:
            peer_ip: IP del peer
            peer_port: Puerto gRPC de upload del peer
            filename: Nombre del archivo
            file_data: Contenido del archivo
            timeout: Timeout en segundos
            
        Returns:
            dict: Resultado de la subida {'success': bool, 'message': str, 'hash': str}
        """
        timeout = timeout or self.default_timeout
        
        try:
            channel = grpc.aio.insecure_channel(f"{peer_ip}:{peer_port}")
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            
            stub = file_service_pb2_grpc.FileTransferStub(channel)
            
            chunks = []
            for i in range(0, len(file_data), self.chunk_size):
                chunk_data = file_data[i:i + self.chunk_size]
                is_last = (i + self.chunk_size) >= len(file_data)
                
                chunk = file_service_pb2.FileChunk(
                    filename=filename,
                    content=chunk_data,
                    offset=i,
                    is_last=is_last
                )
                chunks.append(chunk)
            
            async def chunk_generator():
                for chunk in chunks:
                    yield chunk
            
            response = await stub.UploadFile(chunk_generator())
            await channel.close()
            
            return {
                'success': response.success,
                'message': response.message,
                'hash': response.file_hash
            }
            
        except Exception as e:
            logger.error(f"[GRPC] Error subiendo {filename} a {peer_ip}:{peer_port}: {str(e)}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'hash': None
            }
    
    async def list_files_from_peer(
        self,
        peer_ip: str,
        peer_port: int,
        filter_name: str = None,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Lista archivos disponibles en un peer
        
        Args:
            peer_ip: IP del peer
            peer_port: Puerto gRPC de listado del peer
            filter_name: Filtro opcional por nombre
            timeout: Timeout en segundos
            
        Returns:
            List[Dict]: Lista de archivos [{'filename': str, 'file_size': int, 'file_hash': str}]
        """
        timeout = timeout or self.default_timeout
        
        try:
            channel = grpc.aio.insecure_channel(f"{peer_ip}:{peer_port}")
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            
            stub = file_service_pb2_grpc.FileTransferStub(channel)
            request = file_service_pb2.ListFilesRequest(filter=filter_name or "")
            
            response = await stub.ListFiles(request)
            await channel.close()
            
            files = []
            for file_info in response.files:
                files.append({
                    'filename': file_info.filename,
                    'file_size': file_info.file_size,
                    'file_hash': file_info.file_hash,
                    'last_modified': file_info.last_modified
                })
            
            logger.debug(f"[GRPC] Listados {len(files)} archivos desde {peer_ip}:{peer_port}")
            return files
            
        except Exception as e:
            logger.error(f"[GRPC] Error listando archivos desde {peer_ip}:{peer_port}: {str(e)}")
            return []
    
    async def get_file_info_from_peer(
        self,
        peer_ip: str,
        peer_port: int,
        filename: str,
        timeout: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un archivo específico de un peer
        
        Args:
            peer_ip: IP del peer
            peer_port: Puerto gRPC del peer
            filename: Nombre del archivo
            timeout: Timeout en segundos
            
        Returns:
            Dict: Información del archivo o None si no existe
        """
        timeout = timeout or self.default_timeout
        
        try:
            channel = grpc.aio.insecure_channel(f"{peer_ip}:{peer_port}")
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            
            stub = file_service_pb2_grpc.FileTransferStub(channel)
            request = file_service_pb2.FileInfoRequest(filename=filename)
            
            response = await stub.GetFileInfo(request)
            await channel.close()
            
            return {
                'filename': response.filename,
                'file_size': response.file_size,
                'file_hash': response.file_hash,
                'last_modified': response.last_modified
            }
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                logger.debug(f"[GRPC] Archivo {filename} no encontrado en {peer_ip}:{peer_port}")
                return None
            else:
                logger.error(f"[GRPC] Error obteniendo info de {filename}: {e.details()}")
                return None
        except Exception as e:
            logger.error(f"[GRPC] Error inesperado obteniendo info de {filename}: {str(e)}")
            return None
    
    async def ping_peer(self, peer_ip: str, peer_port: int, timeout: int = 5) -> bool:
        """
        Verifica si un peer está disponible
        
        Args:
            peer_ip: IP del peer
            peer_port: Puerto gRPC del peer
            timeout: Timeout en segundos
            
        Returns:
            bool: True si peer responde, False si no
        """
        try:
            channel = grpc.aio.insecure_channel(f"{peer_ip}:{peer_port}")
            await asyncio.wait_for(channel.channel_ready(), timeout=timeout)
            await channel.close()
            return True
        except:
            return False
