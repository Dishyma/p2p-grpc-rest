import asyncio
import os
import hashlib
import logging
from pathlib import Path
from typing import AsyncIterator

import grpc
import aiofiles

from ...core.path_setup import setup_paths
setup_paths()
import file_service_pb2
import file_service_pb2_grpc
from ...core.config import config

logger = logging.getLogger(__name__)

class UploadFileServicer(file_service_pb2_grpc.FileTransferServicer):
    """Microservicio gRPC dedicado exclusivamente a la subida de archivos"""

    def __init__(self):
        self.files_directory = Path(config.files_directory)

    async def UploadFile(self, request_iterator: AsyncIterator[file_service_pb2.FileChunk], context) -> file_service_pb2.UploadResponse:
        """Subir archivo al peer"""
        try:
            client_info = context.peer()
            
            first_chunk = await request_iterator.__anext__()
            filename = first_chunk.filename

            logger.info(f"[UPLOAD] Solicitud de subida en puerto {config.grpc_upload_port}: {filename}")
            logger.info(f"[UPLOAD] Cliente: {client_info}")
            logger.info(f"[UPLOAD] Directorio destino: {self.files_directory}")

            temp_file_path = self.files_directory / f"{filename}.tmp"
            final_file_path = self.files_directory / filename

            file_hash = hashlib.sha256()

            async with aiofiles.open(temp_file_path, 'wb') as file:
                await file.write(first_chunk.content)
                file_hash.update(first_chunk.content)

                async for chunk in request_iterator:
                    if chunk.filename != filename:
                        continue

                    await file.write(chunk.content)
                    file_hash.update(chunk.content)

                    if chunk.is_last:
                        break

            temp_file_path.rename(final_file_path)

            final_hash = file_hash.hexdigest()

            logger.info(f"[UPLOAD] Subida completada en puerto {config.grpc_upload_port}: {filename} (hash: {final_hash})")
            logger.info(f"[UPLOAD] Archivo guardado en: {final_file_path}")

            return file_service_pb2.UploadResponse(
                success=True,
                message=f"Archivo {filename} subido exitosamente",
                file_hash=final_hash
            )

        except Exception as e:
            logger.error(f"[UPLOAD] Error subiendo archivo: {str(e)}")
            return file_service_pb2.UploadResponse(
                success=False,
                message=f"Error subiendo archivo: {str(e)}",
                file_hash=""
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

async def serve_upload_grpc(servicer: UploadFileServicer) -> None:
    """Iniciar servidor gRPC para Upload"""
    server = grpc.aio.server()
    file_service_pb2_grpc.add_FileTransferServicer_to_server(
        servicer, server
    )

    bind_address = f"0.0.0.0:{config.grpc_upload_port}"
    public_address = f"{config.peer_ip}:{config.grpc_upload_port}"
    server.add_insecure_port(bind_address)

    logger.info(f"[UPLOAD] Iniciando servidor gRPC Upload en {bind_address} (público: {public_address})")
    logger.info(f"[UPLOAD] Microservicio Upload independiente listo en puerto {config.grpc_upload_port}")

    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("[UPLOAD] Deteniendo servidor gRPC Upload...")
        await server.stop(0)
