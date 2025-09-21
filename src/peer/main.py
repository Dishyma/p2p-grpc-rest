import asyncio
import signal
import sys
from pathlib import Path

# Agregar src al path para imports
src_path = Path(__file__).parent.parent
gen_path = src_path / "generated"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(gen_path) not in sys.path:
    sys.path.insert(0, str(gen_path))

# Configurar logging profesional
from .logging_config import setup_peer_logging, get_logger
from .config import config
from .grpc_services.file_service import serve_grpc
from .peer_manager import PeerManager
from .api_server import start_api_server

async def main():
    """Punto de entrada principal para la aplicación del peer."""
    # Configurar logging profesional
    logger = setup_peer_logging(config.peer_name, config.log_level)
    
    logger.info(f"Starting P2P Peer (Name: {config.peer_name})")

    # 1. Crear una única instancia del gestor del peer
    peer_manager = PeerManager()

    # 2. Iniciar los servicios de fondo (gRPC, registro, heartbeat)
    background_services_task = asyncio.create_task(peer_manager.start_services())

    # 3. Iniciar el servidor API REST (comportamiento por defecto)
    logger.info("Starting REST API mode")
    api_task = asyncio.create_task(start_api_server(peer_manager))
    await asyncio.gather(background_services_task, api_task, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)