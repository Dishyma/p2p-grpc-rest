import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import config
from .rest_client.directory_client import DirectoryClient
from .grpc_services.file_service import FileTransferServicer, serve_grpc

logger = logging.getLogger(__name__)

class PeerManager:
    """Gestor del peer para registro y heartbeat"""

    def __init__(self):
        self.servicer = FileTransferServicer()
        self.is_registered = False
        self.peer_id: Optional[str] = None

    async def _detect_registration_ip(self) -> str:
        """Detectar la IP correcta para registro según el entorno"""
        import socket
        import os
        
        # 1. Si hay una IP específica configurada y no es 0.0.0.0, usarla
        if config.peer_ip and config.peer_ip != "0.0.0.0":
            logger.info(f"[WEB] Usando IP configurada: {config.peer_ip}")
            return config.peer_ip
        
        # 2. Detectar si estamos en Docker
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            logger.info("[DOCKER] Entorno Docker detectado")
            
            # En Docker, obtener la IP real del contenedor
            try:
                # Método 1: Conectar a un socket para obtener la IP local del contenedor
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    # Conectar al gateway de Docker (normalmente 172.x.x.1)
                    s.connect(("172.17.0.1", 80))
                    container_ip = s.getsockname()[0]
                    logger.info(f"[DOCKER] IP del contenedor Docker: {container_ip}")
                    return container_ip
            except Exception as e:
                logger.warning(f"[WARNING] Método 1 falló: {e}")
                
                try:
                    # Método 2: Leer desde /proc/net/route para encontrar la interfaz por defecto
                    import subprocess
                    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                    if result.returncode == 0:
                        ips = result.stdout.strip().split()
                        if ips:
                            container_ip = ips[0]  # Primera IP
                            logger.info(f"[DOCKER] IP del contenedor (hostname -I): {container_ip}")
                            return container_ip
                except Exception as e2:
                    logger.warning(f"[WARNING] Método 2 falló: {e2}")
                
                # Método 3: Usar la IP de la interfaz eth0 (común en Docker)
                try:
                    import netifaces
                    interfaces = netifaces.interfaces()
                    for interface in ['eth0', 'ens160', 'enp0s3']:  # Interfaces comunes
                        if interface in interfaces:
                            addrs = netifaces.ifaddresses(interface)
                            if netifaces.AF_INET in addrs:
                                ip = addrs[netifaces.AF_INET][0]['addr']
                                logger.info(f"[DOCKER] IP del contenedor ({interface}): {ip}")
                                return ip
                except ImportError:
                    logger.warning("[WARNING] netifaces no disponible")
                except Exception as e3:
                    logger.warning(f"[WARNING] Método 3 falló: {e3}")
                
                # Fallback: usar localhost
                logger.warning("[DOCKER] Usando localhost como fallback en Docker")
                return "127.0.0.1"
        
        # 3. Entorno local/AWS - obtener IP real
        try:
            # Método más confiable para obtener IP local
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                logger.info(f"[WEB] IP local detectada: {local_ip}")
                return local_ip
        except Exception as e:
            logger.warning(f"[WARNING] No se pudo detectar IP local: {e}")
            
            # Último fallback
            logger.info("[WEB] Usando localhost como fallback")
            return "127.0.0.1"

    async def register_with_directory_server(self) -> bool:
        """Registrar el peer con el directory server"""
        if self.is_registered and self.peer_id:
            logger.info(f"[SUCCESS] Peer ya registrado con ID: {self.peer_id}")
            return True

        logger.info("Iniciando proceso de registro y anuncio...")

        # Verificar configuración antes de intentar registro
        logger.info(f"Configuración: IP={config.peer_ip}, Port={config.grpc_port}, URL={config.directory_server_url}")

        try:
            async with DirectoryClient() as client:
                logger.info("[CONNECTION] Conectando con directory server...")
                # Detectar IP real para registro según el entorno
                registration_ip = await self._detect_registration_ip()
                logger.info(f"[WEB] IP detectada para registro: {registration_ip}")
                
                # Registrar con credenciales (crea usuario y devuelve token automáticamente)
                registration_data = await client.register_peer(
                    config.peer_name, 
                    config.peer_password,
                    registration_ip, 
                    config.grpc_port
                )
                
                if registration_data:
                    self.peer_id = registration_data.get("peer_id")

            if self.peer_id:
                self.is_registered = True
                # Guardar el peer_id en la configuración global
                config.set_registered_peer_id(self.peer_id)
                logger.info(f"[SUCCESS] Peer registrado exitosamente con ID: {self.peer_id}")
                # Anunciar archivos después de un registro exitoso
                await self.update_files()
                return True
            else:
                self.is_registered = False
                logger.error("[ERROR] Error registrando peer: No se recibió peer_id")
                return False

        except Exception as e:
            self.is_registered = False
            logger.error(f"[ERROR] Excepción durante registro: {str(e)}")
            return False

    async def start_heartbeat(self) -> None:
        """Iniciar envío de heartbeats"""
        logger.info("[HEARTBEAT] Iniciando bucle de heartbeat...")

        while True:
            try:
                if self.is_registered:
                    logger.debug(f"[HEARTBEAT] Enviando heartbeat para peer_id: {self.peer_id}")
                    async with DirectoryClient() as client:
                        # Reautenticar si no hay token
                        if not config.get_directory_access_token():
                            await client.login()
                        success = await client.send_heartbeat(self.peer_id)
                    if success:
                        logger.debug("[HEARTBEAT] Heartbeat enviado exitosamente")
                    else:
                        logger.warning(f"[WARNING] Error enviando heartbeat para peer_id: {self.peer_id}")
                        logger.warning("[PROCESSING] Intentando re-registro...")
                        self.is_registered = False  # Marcar como no registrado para reintentar
                else:
                    # Si no estamos registrados, intentar de nuevo
                    logger.info("[PROCESSING] Peer no registrado, intentando registro...")
                    await self.register_with_directory_server()

                # Esperar intervalo configurado
                logger.debug(f"[TIMER] Esperando {config.heartbeat_interval} segundos...")
                await asyncio.sleep(config.heartbeat_interval)

            except Exception as e:
                logger.error(f"Error en heartbeat: {str(e)}")
                await asyncio.sleep(config.heartbeat_interval)

    async def _get_local_files_info(self) -> List[Dict[str, Any]]:
        """Obtener información de archivos locales"""
        files_info = []

        try:
            for file_path in Path(config.files_directory).iterdir():
                if file_path.is_file():
                    stat = file_path.stat()

                    # Calcular hash del archivo
                    file_hash = await self.servicer._calculate_file_hash(file_path)

                    file_info = {
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "hash": file_hash
                    }

                    files_info.append(file_info)

        except Exception as e:
            logger.error(f"Error obteniendo información de archivos: {str(e)}")

        return files_info

    async def _cleanup_removed_files(self, current_local_filenames: set) -> None:
        """Eliminar del directory server los archivos que ya no existen localmente"""
        try:
            peer_id = config.get_registered_peer_id() or self.peer_id
            if not peer_id:
                logger.warning("No hay peer_id para limpiar archivos")
                return
                
            async with DirectoryClient() as client:
                # Asegurar login
                if not config.get_directory_access_token():
                    await client.login()
                # Obtener la lista de archivos que el servidor cree que tenemos
                server_files = await client.get_peer_files_list(peer_id)
                
                if server_files:
                    server_filenames = {f.get("filename") for f in server_files}
                    
                    # Encontrar archivos que están en el servidor pero no localmente
                    removed_files = server_filenames - current_local_filenames
                    
                    if removed_files:
                        logger.info(f"[CLEANUP] Limpiando {len(removed_files)} archivos eliminados: {list(removed_files)}")
                        
                        # Eliminar cada archivo del servidor
                        for filename in removed_files:
                            success = await client.remove_peer_file(peer_id, filename)
                            if success:
                                logger.debug(f"[SUCCESS] Eliminado '{filename}' del directory server")
                            else:
                                logger.warning(f"[WARNING] No se pudo eliminar '{filename}' del directory server")
                    else:
                        logger.debug("[SUCCESS] No hay archivos para limpiar")
                        
        except Exception as e:
            logger.error(f"Error limpiando archivos eliminados: {str(e)}")

    async def announce_new_file(self, filename: str, file_size: int, file_hash: str) -> None:
        """Anuncia un único archivo nuevo al directory server."""
        # Usar el peer_id de la configuración global
        peer_id = config.get_registered_peer_id() or self.peer_id
        if not peer_id:
            # Intentar registrarse automáticamente antes de abandonar
            logger.info("[PROCESSING] Peer no registrado. Intentando registro automático antes de anunciar archivo...")
            try:
                success = await self.register_with_directory_server()
                if success:
                    peer_id = config.get_registered_peer_id() or self.peer_id
                else:
                    logger.warning("Peer no registrado, no se puede anunciar el nuevo archivo.")
                    return
            except Exception as e:
                logger.warning(f"Peer no registrado, no se puede anunciar el nuevo archivo. Motivo: {e}")
                return

        file_metadata = [{
            "filename": filename,
            "size": file_size,
            "hash": file_hash
        }]

        try:
            async with DirectoryClient() as client:
                # Asegurar sesión válida
                if not config.get_directory_access_token():
                    await client.login()
                success = await client.announce_files(peer_id, file_metadata)
            if success:
                logger.info(f"[SUCCESS] Nuevo archivo '{filename}' anunciado exitosamente.")
            else:
                logger.error(f"[ERROR] Error anunciando el nuevo archivo '{filename}'.")
        except Exception as e:
            logger.error(f"Excepción anunciando nuevo archivo: {e}")

    async def announce_one_file_by_name(self, filename: str) -> None:
        """Calcula metadatos y anuncia un solo archivo por nombre."""
        try:
            file_path = Path(config.files_directory) / filename
            if not file_path.exists() or not file_path.is_file():
                logger.error(f"Archivo '{filename}' no existe en el directorio local: {config.files_directory}")
                return

            stat = file_path.stat()
            # Calcular hash usando el servicer local
            file_hash = await self.servicer._calculate_file_hash(file_path)
            await self.announce_new_file(filename, stat.st_size, file_hash)
        except Exception as e:
            logger.error(f"Error anunciando archivo por nombre '{filename}': {e}")

    async def update_files(self) -> None:
        """Sincronizar archivos locales con el directory server (con limpieza)"""
        # Si no tenemos peer_id, intentar re-registrarse
        peer_id = config.get_registered_peer_id() or self.peer_id
        if not peer_id:
            logger.info("[PROCESSING] No hay peer_id, intentando registro...")
            success = await self.register_with_directory_server()
            if not success:
                logger.error("[ERROR] No se pudo registrar el peer para actualizar archivos")
                return

        try:
            # 1. Obtener archivos locales actuales
            local_files = await self._get_local_files_info()
            local_filenames = {f["filename"] for f in local_files}
            
            # 2. Anunciar archivos actuales
            peer_id = config.get_registered_peer_id() or self.peer_id
            async with DirectoryClient() as client:
                success = await client.announce_files(peer_id, local_files)
                
                if success:
                    logger.info(f"[SUCCESS] {len(local_files)} archivos sincronizados con directory server")
                    
                    # 3. Limpiar archivos que ya no existen localmente
                    await self._cleanup_removed_files(local_filenames)
                    
                else:
                    logger.error("[ERROR] Error sincronizando archivos")

        except Exception as e:
            logger.error(f"Error sincronizando archivos: {str(e)}")

    async def start_services(self):
        """Inicia todos los servicios de fondo del peer: gRPC y el bucle de heartbeat/registro."""
        logger.info("[START] Iniciando servicios de fondo del peer...")

        # Dar tiempo para que el servidor de directorio inicie
        await asyncio.sleep(10)

        # Tarea 1: Iniciar servidor gRPC para atender descargas
        grpc_server_task = asyncio.create_task(serve_grpc(self.servicer))

        # Tarea 2: Iniciar el bucle de registro y heartbeats
        heartbeat_task = asyncio.create_task(self.start_heartbeat())

        logger.info("[SUCCESS] Servicios de fondo iniciados (gRPC y Heartbeat).")

        # Guardar referencias a las tareas para poder cancelarlas
        self.background_tasks = [grpc_server_task, heartbeat_task]

    async def stop_services(self):
        """Detiene todos los servicios de fondo del peer."""
        logger.info("[STOP] Deteniendo servicios de fondo...")
        for task in getattr(self, 'background_tasks', []):
            task.cancel()
        
        # Detener el servidor gRPC explícitamente si está corriendo
        grpc_server = getattr(self.servicer, 'server', None)
        if grpc_server:
            await grpc_server.stop(grace=1)
            logger.info("Servidor gRPC detenido.")

    async def logout(self) -> bool:
        """Realiza el proceso de logout completo del peer."""
        logger.info("Iniciando proceso de logout...")

        # 1. Informar al directory server
        try:
            async with DirectoryClient() as client:
                await client.logout()
        except Exception as e:
            logger.error(f"No se pudo contactar al directory server para el logout: {str(e)}")
            # Continuamos el proceso de todos modos

        # 2. Detener los servicios de fondo
        await self.stop_services()

        # 3. Limpiar estado local
        self.is_registered = False
        self.peer_id = None
        config.clear_session()

        logger.info("Logout completado. El peer está ahora inactivo.")
        return True
        
    def get_registration_status(self) -> Dict[str, Any]:
        """Obtener el estado actual de registro del peer"""
        return {
            "peer_id": self.peer_id,
            "is_registered": self.is_registered,
            "config_peer_id": config.get_registered_peer_id()
        }
