import asyncio
import signal
import sys
from pathlib import Path

# Setup de paths para imports
from .core.path_setup import setup_paths
setup_paths()

from .core.logging_config import setup_peer_logging, get_logger
from .core.config import config
from .core.peer_manager import PeerManager
from .services.rest.api_server import start_api_server

async def main():
    """Punto de entrada principal para la aplicación del peer."""
    logger = setup_peer_logging(config.peer_name, config.log_level)
    
    logger.info(f"Starting P2P Peer (Name: {config.peer_name})")

    peer_manager = PeerManager()

    background_services_task = asyncio.create_task(peer_manager.start_services())

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