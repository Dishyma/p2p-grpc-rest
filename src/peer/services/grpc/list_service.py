import asyncio
import os
import hashlib
import logging
from pathlib import Path

import grpc
import aiofiles

from ...core.path_setup import setup_paths
setup_paths()
import file_service_pb2
import file_service_pb2_grpc
from ...core.config import config

logger = logging.getLogger(__name__)

class ListFilesServicer(file_service_pb2_grpc.FileTransferServicer):
    """Microservicio gRPC dedicado exclusivamente al listado de archivos"""

    def __init__(self):
        self.files_directory = Path(config.files_directory)

    async def ListFiles(self, request: file_service_pb2.ListFilesRequest, context) -> file_service_pb2.ListFilesResponse:
        """Listar archivos disponibles en el peer"""
        try:
            client_info = context.peer()
            filter_pattern = request.filter.lower() if request.filter else ""
            
            logger.info(f"[LIST] Solicitud de listado en puerto {config.grpc_list_port}")
            logger.info(f"[LIST] Cliente: {client_info}")
            logger.info(f"[LIST] Filtro aplicado: '{filter_pattern}' (vacío = sin filtro)")
            logger.info(f"[LIST] Directorio: {self.files_directory}")

            files_info = []

            for file_path in self.files_directory.iterdir():
                if file_path.is_file():
                    filename = file_path.name

                    if filter_pattern and filter_pattern not in filename.lower():
                        continue

                    stat = file_path.stat()
                    file_hash = await self._calculate_file_hash(file_path)

                    file_info = file_service_pb2.FileInfo(
                        filename=filename,
                        file_size=stat.st_size,
                        file_hash=file_hash,
                        last_modified=str(stat.st_mtime)
                    )

                    files_info.append(file_info)

            logger.info(f"[LIST] Listado completado en puerto {config.grpc_list_port}: {len(files_info)} archivos encontrados")
            return file_service_pb2.ListFilesResponse(files=files_info)

        except Exception as e:
            logger.error(f"[LIST] Error listando archivos: {str(e)}")
            return file_service_pb2.ListFilesResponse(files=[])

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

async def serve_list_grpc(servicer: ListFilesServicer) -> None:
    """Iniciar servidor gRPC para List"""
    server = grpc.aio.server()
    file_service_pb2_grpc.add_FileTransferServicer_to_server(
        servicer, server
    )

    bind_address = f"0.0.0.0:{config.grpc_list_port}"
    public_address = f"{config.peer_ip}:{config.grpc_list_port}"
    server.add_insecure_port(bind_address)

    logger.info(f"[LIST] Iniciando servidor gRPC List en {bind_address} (público: {public_address})")
    logger.info(f"[LIST] Microservicio List independiente listo en puerto {config.grpc_list_port}")

    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("[LIST] Deteniendo servidor gRPC List...")
        await server.stop(0)
