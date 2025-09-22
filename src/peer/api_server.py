import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel
import uvicorn
import aiofiles
import hashlib

from .config import config
from .peer_manager import PeerManager
from .file_discovery import FileDiscoveryService
from .rest_client.directory_client import DirectoryClient
from ..generated import file_service_pb2, file_service_pb2_grpc
import grpc

logger = logging.getLogger(__name__)

# Modelos Pydantic para Swagger
class PeerStatus(BaseModel):
    peer_name: str
    peer_id: Optional[str]
    is_registered: bool
    config_peer_id: Optional[str]
    ip_address: str
    grpc_port: int
    directory_server: Dict[str, Any]
    local_files_count: int
    files_directory: str

class FileInfo(BaseModel):
    filename: str
    size: int
    modified: float

class LocalFilesResponse(BaseModel):
    files: List[FileInfo]
    total: int
    directory: str

class SearchFilesResponse(BaseModel):
    filename: str
    peers: List[Dict[str, Any]]
    total_peers: int

class PeersResponse(BaseModel):
    peers: List[Dict[str, Any]]
    total: int

class SuccessMessage(BaseModel):
    message: str

class UploadResponse(BaseModel):
    message: str
    filename: str
    size: int
    hash: str

class RegisterResponse(BaseModel):
    message: str
    peer_id: str

class DownloadRequest(BaseModel):
    filename: str
    peer_id: Optional[str] = None

class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

class TokenValidationResponse(BaseModel):
    is_valid: bool
    message: str
    details: Optional[Dict[str, Any]] = None

app = FastAPI(
    title="🌐 Peer P2P API",
    description="""
    ## API REST para interactuar con el peer P2P
    
    Esta API permite:
    - 📊 Ver el estado del peer
    - 📁 Listar archivos locales y de otros peers
    - 🔍 Buscar archivos en la red P2P
    - ⬇️ Descargar archivos desde otros peers (con failover)
    - ⬆️ Subir archivos usando gRPC UploadFile
    - 📢 Anunciar archivos al directory server
    - 🔗 Registrarse con el directory server
    - 👥 Ver peers activos en la red
    
    ### Flujo típico:
    1. Verificar estado con `/status`
    2. Registrar peer con `/register` (si no está registrado)
    3. Subir archivos con `/files/upload`
    4. Anunciar archivos con `/files/announce`
    5. Buscar archivos con `/files/search`
    6. Descargar archivos con `/files/download`
    
    """,
    version="1.0.0",
    contact={
        "name": "P2P System",
        "email": "admin@example.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Variable global para el peer manager
peer_manager: Optional[PeerManager] = None
file_discovery: Optional[FileDiscoveryService] = None

def get_peer_manager() -> PeerManager:
    """Dependency para obtener el peer manager"""
    if peer_manager is None:
        raise HTTPException(status_code=500, detail="Peer manager not initialized")
    return peer_manager

def get_file_discovery() -> FileDiscoveryService:
    """Dependency para obtener el file discovery service"""
    if file_discovery is None:
        raise HTTPException(status_code=500, detail="File discovery service not initialized")
    return file_discovery

async def _upload_via_grpc(filename: str, content: bytes, pm: PeerManager) -> Dict[str, Any]:
    """Subir archivo usando gRPC UploadFile internamente"""
    try:
        # Conectar al servicio gRPC Upload del peer
        channel = grpc.aio.insecure_channel(f"localhost:{config.grpc_upload_port}")
        stub = file_service_pb2_grpc.FileTransferStub(channel)
        
        # Crear chunks del archivo
        chunk_size = 64 * 1024  # 64KB chunks
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunk_data = content[i:i + chunk_size]
            is_last = (i + chunk_size) >= len(content)
            
            chunk = file_service_pb2.FileChunk(
                filename=filename,
                content=chunk_data,
                offset=i,
                is_last=is_last
            )
            chunks.append(chunk)
        
        # Enviar chunks via gRPC
        async def chunk_generator():
            for chunk in chunks:
                yield chunk
        
        # Llamar al servicio UploadFile
        response = await stub.UploadFile(chunk_generator())
        
        await channel.close()
        
        return {
            'success': response.success,
            'message': response.message,
            'hash': response.file_hash
        }
        
    except Exception as e:
        logger.error(f"Error en upload gRPC: {str(e)}")
        # Fallback: guardar directamente
        file_path = Path(config.files_directory) / filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        file_hash = hashlib.sha256(content).hexdigest()
        return {
            'success': True,
            'message': f'Archivo {filename} guardado (fallback)',
            'hash': file_hash
        }

@app.get("/", 
         summary="🏠 Página principal",
         description="Endpoint raíz que muestra información básica del peer")
async def root():
    """Endpoint raíz"""
    return {"message": "Peer P2P API", "peer_name": config.peer_name}

@app.post("/auth/validate", 
          response_model=TokenValidationResponse,
          summary="🔑 Validar sesión actual",
          description="Verifica si el token de sesión del peer con el directory server es válido.")
async def validate_session():
    """Validar el estado del token de autenticación del peer."""
    try:
        async with DirectoryClient() as client:
            validation_data = await client.validate_token()
            
            if validation_data and validation_data.get("valid"):
                return TokenValidationResponse(
                    is_valid=True,
                    message="La sesión con el directory server es válida.",
                    details=validation_data
                )
            else:
                return TokenValidationResponse(
                    is_valid=False,
                    message="La sesión no es válida o ha expirado.",
                    details=validation_data
                )
    except Exception as e:
        logger.error(f"Error durante la validación del token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al contactar el directory server: {str(e)}"
        )

@app.post("/auth/logout", 
          response_model=SuccessMessage,
          summary="🔒 Cerrar sesión",
          description="Cierra la sesión del peer, lo marca como inactivo en el directory server y detiene los servicios.")
async def logout_session(pm: PeerManager = Depends(get_peer_manager)):
    """Cierra la sesión actual del peer."""
    try:
        success = await pm.logout()
        if success:
            return SuccessMessage(message="Sesión cerrada exitosamente.")
        else:
            raise HTTPException(status_code=500, detail="Ocurrió un error durante el logout.")
    except Exception as e:
        logger.error(f"Error durante el logout: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/status", 
         response_model=PeerStatus,
         summary="📊 Estado del peer",
         description="Obtiene el estado completo del peer incluyendo registro, conectividad y archivos")
async def get_status(pm: PeerManager = Depends(get_peer_manager)):
    """Obtener estado del peer"""
    try:
        status = pm.get_registration_status()
        
        # Verificar conectividad con directory server
        try:
            async with DirectoryClient() as client:
                peers = await client.get_active_peers()
                directory_status = "connected"
                peers_count = len(peers)
        except Exception:
            directory_status = "disconnected"
            peers_count = 0

        # Contar archivos locales
        files_directory = Path(config.files_directory)
        local_files_count = sum(1 for _ in files_directory.iterdir() if _.is_file())

        return {
            "peer_name": config.peer_name,
            "peer_id": status["peer_id"],
            "is_registered": status["is_registered"],
            "config_peer_id": status["config_peer_id"],
            "ip_address": config.peer_ip,
            "grpc_download_port": config.grpc_download_port,
            "grpc_upload_port": config.grpc_upload_port,
            "grpc_list_port": config.grpc_list_port,
            "directory_server": {
                "url": config.directory_server_url,
                "status": directory_status,
                "peers_count": peers_count,
                "auth": {
                    "has_token": bool(config.get_directory_access_token())
                }
            },
            "local_files_count": local_files_count,
            "files_directory": str(files_directory)
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/announce_one",
          response_model=SuccessMessage,
          summary="📢 Anunciar un archivo",
          description="Anuncia un único archivo local al directory server por su nombre")
async def announce_one_file(
    request: DownloadRequest,
    pm: PeerManager = Depends(get_peer_manager)
):
    """Anunciar un archivo específico al directory server"""
    try:
        await pm.announce_one_file_by_name(request.filename)
        return {"message": f"Archivo '{request.filename}' anunciado exitosamente"}
    except Exception as e:
        logger.error(f"Error announcing single file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login",
          response_model=SuccessMessage,
          summary="🔐 Iniciar sesión",
          description="Inicia sesión contra el directory server y guarda el token para futuras llamadas")
async def login(request: LoginRequest):
    try:
        async with DirectoryClient() as client:
            ok = await client.login(request.username, request.password)
            if not ok:
                raise HTTPException(status_code=401, detail="Credenciales inválidas o error de login")
        return {"message": "Login exitoso. Token almacenado"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/local", 
         response_model=LocalFilesResponse,
         summary="📁 Archivos locales",
         description="Lista todos los archivos disponibles en el directorio local del peer")
async def list_local_files():
    """Listar archivos locales"""
    try:
        files_directory = Path(config.files_directory)
        files = []
        
        for file_path in files_directory.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        return {
            "files": files,
            "total": len(files),
            "directory": str(files_directory)
        }
    except Exception as e:
        logger.error(f"Error listing local files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/search", 
         response_model=SearchFilesResponse,
         summary="🔍 Buscar archivos",
         description="Busca un archivo específico en toda la red P2P")
async def search_files(
    filename: str = Query(..., description="Nombre del archivo a buscar", example="document.pdf"),
    fd: FileDiscoveryService = Depends(get_file_discovery)
):
    """Buscar archivos en la red P2P"""
    try:
        peers = await fd.find_file(filename)
        return {
            "filename": filename,
            "peers": peers,
            "total_peers": len(peers)
        }
    except Exception as e:
        logger.error(f"Error searching files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/download", 
          response_model=SuccessMessage,
          summary="⬇️ Descargar archivo",
          description="Descarga un archivo desde la red P2P al directorio local")
async def download_file(
    request: DownloadRequest,
    fd: FileDiscoveryService = Depends(get_file_discovery)
):
    """Descargar archivo desde la red P2P"""
    try:
        success = await fd.download_file(request.filename, preferred_peer_id=request.peer_id)
        if success:
            return {"message": f"Archivo '{request.filename}' descargado exitosamente"}
        else:
            raise HTTPException(status_code=404, detail=f"No se pudo descargar '{request.filename}'")
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/upload", 
          response_model=UploadResponse,
          summary="⬆️ Subir archivo",
          description="Sube un archivo al peer local usando gRPC UploadFile internamente")
async def upload_file(
    file: UploadFile = File(..., description="Archivo a subir"),
    pm: PeerManager = Depends(get_peer_manager)
):
    """Subir un archivo al peer local usando gRPC UploadFile"""
    try:
        # Validar archivo
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nombre de archivo requerido")
        
        # Crear ruta de destino
        file_path = Path(config.files_directory) / file.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Leer contenido del archivo
        content = await file.read()
        file_size = len(content)
        
        # Usar gRPC UploadFile internamente
        upload_result = await _upload_via_grpc(file.filename, content, pm)
        
        logger.info(f"[FILE] Archivo '{file.filename}' subido exitosamente ({file_size} bytes)")
        
        # Anunciar archivo al directory server
        await pm.announce_new_file(file.filename, file_size, upload_result['hash'])
        
        return UploadResponse(
            message=f"Archivo '{file.filename}' subido exitosamente",
            filename=file.filename,
            size=file_size,
            hash=upload_result['hash']
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/announce", 
          response_model=SuccessMessage,
          summary="📢 Anunciar archivos",
          description="Anuncia todos los archivos locales al directory server para que otros peers los puedan encontrar")
async def announce_files(pm: PeerManager = Depends(get_peer_manager)):
    """Anunciar todos los archivos locales al directory server"""
    try:
        await pm.update_files()
        return {"message": "Archivos anunciados exitosamente"}
    except Exception as e:
        logger.error(f"Error announcing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register", 
          response_model=RegisterResponse,
          summary="🔗 Registrar peer",
          description="Fuerza el registro del peer con el directory server")
async def force_register(pm: PeerManager = Depends(get_peer_manager)):
    """Forzar registro con el directory server"""
    try:
        success = await pm.register_with_directory_server()
        if success:
            return {"message": "Peer registrado exitosamente", "peer_id": pm.peer_id}
        else:
            raise HTTPException(status_code=500, detail="Error registrando peer")
    except Exception as e:
        logger.error(f"Error registering peer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/peers", 
         response_model=PeersResponse,
         summary="👥 Peers activos",
         description="Obtiene la lista de todos los peers activos en la red P2P")
async def get_active_peers():
    """Obtener peers activos de la red"""
    try:
        async with DirectoryClient() as client:
            peers = await client.get_active_peers()
            return {
                "peers": peers,
                "total": len(peers)
            }
    except Exception as e:
        logger.error(f"Error getting active peers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/peer/{peer_id}", 
         response_model=Dict[str, Any],
         summary="📁 Archivos de peer específico",
         description="Obtiene archivos de un peer específico usando gRPC ListFiles directamente")
async def get_peer_files(
    peer_id: str,
    fd: FileDiscoveryService = Depends(get_file_discovery)
):
    """Obtener archivos de un peer específico usando gRPC"""
    try:
        # Buscar el peer en el directory server
        async with DirectoryClient() as client:
            peers = await client.get_active_peers()
        
        # Encontrar el peer específico
        target_peer = None
        for peer in peers:
            if peer.get('peer_id') == peer_id:
                target_peer = peer
                break
        
        if not target_peer:
            raise HTTPException(status_code=404, detail=f"Peer {peer_id} no encontrado o inactivo")
        
        # Usar gRPC ListFiles directamente
        files = await fd._get_peer_files(target_peer)
        
        return {
            "peer_id": peer_id,
            "peer_info": {
                "ip_address": target_peer.get('ip_address'),
                "grpc_port": target_peer.get('grpc_port')
            },
            "files": files,
            "total_files": len(files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting peer files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def start_api_server(pm: PeerManager):
    """Iniciar servidor API con FastAPI y uvicorn"""
    global peer_manager, file_discovery
    peer_manager = pm
    file_discovery = FileDiscoveryService(pm)
    
    logger.info(f"[WEB] Iniciando FastAPI server en http://{config.peer_ip}:{config.rest_port}")
    
    # Importante: dentro del contenedor debemos escuchar en 0.0.0.0
    # para aceptar conexiones desde fuera del contenedor. La IP pública
    # anunciada al directory server sigue siendo config.peer_ip.
    config_uvicorn = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.rest_port,
        log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)
    await server.serve()
