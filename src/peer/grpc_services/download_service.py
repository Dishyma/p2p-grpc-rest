import asyncio
import os
import hashlib
import logging
from pathlib import Path
from typing import AsyncIterator

import grpc
import aiofiles
from generated import file_service_pb2
from generated import file_service_pb2_grpc
from peer.config import config

logger = logging.getLogger(__name__)

class DownloadFileServicer(file_service_pb2_grpc.FileTransferServicer):
    """Microservicio gRPC dedicado exclusivamente a la descarga de archivos"""

    def __init__(self):
        self.files_directory = Path(config.files_directory)

    async def DownloadFile(self, request: file_service_pb2.DownloadRequest, context) -> AsyncIterator[file_service_pb2.FileChunk]:
        """Descargar archivo desde el peer"""
        filename = request.filename
        file_path = self.files_directory / filename
        
        # Obtener información del cliente
        client_info = context.peer()
        
        logger.info(f"[DOWNLOAD] Solicitud de descarga en puerto {config.grpc_download_port}: {filename}")
        logger.info(f"[DOWNLOAD] Cliente: {client_info}")
        logger.info(f"[DOWNLOAD] Directorio: {self.files_directory}")

        if not file_path.exists():
            logger.error(f"[DOWNLOAD] Archivo no encontrado: {filename}")
            yield file_service_pb2.FileChunk(
                filename=filename,
                content=b"",
                offset=0,
                is_last=True
            )
            return

        try:
            file_size = file_path.stat().st_size
            chunk_size = 64 * 1024  # 64KB chunks
            offset = 0
            chunks_count = 0
            
            logger.info(f"[DOWNLOAD] Archivo encontrado - Tamaño: {file_size} bytes")

            # Calcular hash del archivo si se proporcionó
            if request.file_hash:
                actual_hash = await self._calculate_file_hash(file_path)
                if actual_hash != request.file_hash:
                    logger.warning(f"[DOWNLOAD] Hash mismatch para {filename}")
                    yield file_service_pb2.FileChunk(
                        filename=filename,
                        content=b"",
                        offset=0,
                        is_last=True
                    )
                    return

            async with aiofiles.open(file_path, 'rb') as file:
                while offset < file_size:
                    await file.seek(offset)
                    chunk_data = await file.read(chunk_size)

                    if not chunk_data:
                        break

                    is_last = offset + len(chunk_data) >= file_size

                    yield file_service_pb2.FileChunk(
                        filename=filename,
                        content=chunk_data,
                        offset=offset,
                        is_last=is_last
                    )

                    offset += len(chunk_data)
                    chunks_count += 1

            logger.info(f"[DOWNLOAD] Descarga completada en puerto {config.grpc_download_port}: {filename}")
            logger.info(f"[DOWNLOAD] Total enviado: {offset} bytes en {chunks_count} chunks")

        except Exception as e:
            logger.error(f"[DOWNLOAD] Error descargando archivo {filename}: {str(e)}")
            yield file_service_pb2.FileChunk(
                filename=filename,
                content=b"",
                offset=0,
                is_last=True
            )

    async def GetFileInfo(self, request: file_service_pb2.FileInfoRequest, context) -> file_service_pb2.FileInfo:
        """Obtener información de un archivo específico"""
        filename = request.filename
        file_path = self.files_directory / filename
        
        client_info = context.peer()
        logger.info(f"[DOWNLOAD] Solicitud GetFileInfo en puerto {config.grpc_download_port}: {filename}")
        logger.info(f"[DOWNLOAD] Cliente: {client_info}")

        if not file_path.exists():
            logger.warning(f"[DOWNLOAD] Archivo no encontrado para GetFileInfo: {filename}")
            return file_service_pb2.FileInfo(
                filename=filename,
                file_size=0,
                file_hash="",
                last_modified=""
            )

        try:
            stat = file_path.stat()
            file_hash = await self._calculate_file_hash(file_path)

            return file_service_pb2.FileInfo(
                filename=filename,
                file_size=stat.st_size,
                file_hash=file_hash,
                last_modified=str(stat.st_mtime)
            )

        except Exception as e:
            logger.error(f"[DOWNLOAD] Error obteniendo info de archivo {filename}: {str(e)}")
            return file_service_pb2.FileInfo(
                filename=filename,
                file_size=0,
                file_hash="",
                last_modified=""
            )

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcular hash SHA256 de un archivo"""
        hash_sha256 = hashlib.sha256()

        async with aiofiles.open(file_path, 'rb') as file:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

async def serve_download_grpc(servicer: DownloadFileServicer) -> None:
    """Iniciar servidor gRPC para Download"""
    server = grpc.aio.server()
    file_service_pb2_grpc.add_FileTransferServicer_to_server(
        servicer, server
    )

    # Bind to download port (base port)
    bind_address = f"0.0.0.0:{config.grpc_download_port}"
    public_address = f"{config.peer_ip}:{config.grpc_download_port}"
    server.add_insecure_port(bind_address)

    logger.info(f"[DOWNLOAD] Iniciando servidor gRPC Download en {bind_address} (público: {public_address})")
    logger.info(f"[DOWNLOAD] Microservicio Download independiente listo en puerto {config.grpc_download_port}")

    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("[DOWNLOAD] Deteniendo servidor gRPC Download...")
        await server.stop(0)
