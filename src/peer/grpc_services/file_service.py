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

class FileTransferServicer(file_service_pb2_grpc.FileTransferServicer):
    """Implementación del servicio gRPC para transferencia de archivos"""

    def __init__(self):
        self.files_directory = Path(config.files_directory)

    async def DownloadFile(self, request: file_service_pb2.DownloadRequest, context) -> AsyncIterator[file_service_pb2.FileChunk]:
        """Descargar archivo desde el peer"""
        filename = request.filename
        file_path = self.files_directory / filename

        logger.info(f"Solicitud de descarga: {filename}")

        if not file_path.exists():
            logger.error(f"Archivo no encontrado: {filename}")
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

            # Calcular hash del archivo si se proporcionó
            if request.file_hash:
                actual_hash = await self._calculate_file_hash(file_path)
                if actual_hash != request.file_hash:
                    logger.warning(f"Hash mismatch para {filename}")
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

            logger.info(f"Descarga completada: {filename}")

        except Exception as e:
            logger.error(f"Error descargando archivo {filename}: {str(e)}")
            yield file_service_pb2.FileChunk(
                filename=filename,
                content=b"",
                offset=0,
                is_last=True
            )

    async def UploadFile(self, request_iterator: AsyncIterator[file_service_pb2.FileChunk], context) -> file_service_pb2.UploadResponse:
        """Subir archivo al peer"""
        try:
            # Recopilar información del primer chunk
            first_chunk = await request_iterator.__anext__()
            filename = first_chunk.filename

            logger.info(f"Solicitud de subida: {filename}")

            # Crear archivo temporal para escritura
            temp_file_path = self.files_directory / f"{filename}.tmp"
            final_file_path = self.files_directory / filename

            file_hash = hashlib.sha256()

            async with aiofiles.open(temp_file_path, 'wb') as file:
                # Escribir primer chunk
                await file.write(first_chunk.content)
                file_hash.update(first_chunk.content)

                # Procesar chunks restantes
                async for chunk in request_iterator:
                    if chunk.filename != filename:
                        continue  # Ignorar chunks de otros archivos

                    await file.write(chunk.content)
                    file_hash.update(chunk.content)

                    if chunk.is_last:
                        break

            # Mover archivo temporal a final
            temp_file_path.rename(final_file_path)

            final_hash = file_hash.hexdigest()

            logger.info(f"Subida completada: {filename} (hash: {final_hash})")

            return file_service_pb2.UploadResponse(
                success=True,
                message=f"Archivo {filename} subido exitosamente",
                file_hash=final_hash
            )

        except Exception as e:
            logger.error(f"Error subiendo archivo: {str(e)}")
            return file_service_pb2.UploadResponse(
                success=False,
                message=f"Error subiendo archivo: {str(e)}",
                file_hash=""
            )

    async def ListFiles(self, request: file_service_pb2.ListFilesRequest, context) -> file_service_pb2.ListFilesResponse:
        """Listar archivos disponibles en el peer"""
        try:
            filter_pattern = request.filter.lower() if request.filter else ""

            files_info = []

            for file_path in self.files_directory.iterdir():
                if file_path.is_file():
                    filename = file_path.name

                    # Aplicar filtro si existe
                    if filter_pattern and filter_pattern not in filename.lower():
                        continue

                    # Obtener información del archivo
                    stat = file_path.stat()
                    file_hash = await self._calculate_file_hash(file_path)

                    file_info = file_service_pb2.FileInfo(
                        filename=filename,
                        file_size=stat.st_size,
                        file_hash=file_hash,
                        last_modified=str(stat.st_mtime)
                    )

                    files_info.append(file_info)

            logger.info(f"Listando {len(files_info)} archivos")
            return file_service_pb2.ListFilesResponse(files=files_info)

        except Exception as e:
            logger.error(f"Error listando archivos: {str(e)}")
            return file_service_pb2.ListFilesResponse(files=[])

    async def GetFileInfo(self, request: file_service_pb2.FileInfoRequest, context) -> file_service_pb2.FileInfo:
        """Obtener información de un archivo específico"""
        filename = request.filename
        file_path = self.files_directory / filename

        if not file_path.exists():
            logger.warning(f"Archivo no encontrado para GetFileInfo: {filename}")
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
            logger.error(f"Error obteniendo info de archivo {filename}: {str(e)}")
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

async def serve_grpc(servicer: FileTransferServicer) -> None:
    """Iniciar servidor gRPC"""
    server = grpc.aio.server()
    file_service_pb2_grpc.add_FileTransferServicer_to_server(
        servicer, server
    )

    # Bind to all interfaces (0.0.0.0) but log the public IP for reference
    bind_address = f"0.0.0.0:{config.grpc_port}"
    public_address = f"{config.peer_ip}:{config.grpc_port}"
    server.add_insecure_port(bind_address)

    logger.info(f"Iniciando servidor gRPC en {bind_address} (público: {public_address})")

    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Deteniendo servidor gRPC...")
        await server.stop(0)
