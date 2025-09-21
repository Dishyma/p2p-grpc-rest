"""
Configuración de logging profesional para el componente Peer
"""
import logging
import logging.config
import os
from pathlib import Path

def setup_peer_logging(peer_name: str = "peer", log_level: str = "INFO"):
    """
    Configura el sistema de logging para el peer
    
    Args:
        peer_name: Nombre del peer para identificar logs
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs/peer")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configuración de logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "file": "%(filename)s", "line": %(lineno)d}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file_all': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': f'logs/peer/{peer_name}_all.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': f'logs/peer/{peer_name}_error.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_grpc': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': f'logs/peer/{peer_name}_grpc.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 3,
                'encoding': 'utf8'
            },
            'file_api': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': f'logs/peer/{peer_name}_api.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 3,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            # Logger principal del peer
            'src.peer': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            # Logger específico para gRPC
            'src.peer.grpc_services': {
                'level': 'DEBUG',
                'handlers': ['file_grpc', 'file_error'],
                'propagate': False
            },
            # Logger específico para API REST
            'src.peer.api_server': {
                'level': 'DEBUG',
                'handlers': ['file_api', 'file_error'],
                'propagate': False
            },
            # Logger para file discovery
            'src.peer.file_discovery': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            # Logger para peer manager
            'src.peer.peer_manager': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            # Silenciar logs muy verbosos de librerías externas
            'uvicorn': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'WARNING',
                'handlers': ['file_api'],
                'propagate': False
            },
            'grpc': {
                'level': 'WARNING',
                'handlers': ['file_grpc'],
                'propagate': False
            },
            'aiohttp': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    
    # Aplicar configuración
    logging.config.dictConfig(logging_config)
    
    # Logger principal para el peer
    logger = logging.getLogger('src.peer')
    logger.info(f"Logging system initialized for peer: {peer_name}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log directory: {log_dir.absolute()}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado
    
    Args:
        name: Nombre del logger (ej: 'src.peer.api_server')
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)

# Funciones de conveniencia para diferentes componentes
def get_api_logger() -> logging.Logger:
    """Logger para API REST"""
    return logging.getLogger('src.peer.api_server')

def get_grpc_logger() -> logging.Logger:
    """Logger para servicios gRPC"""
    return logging.getLogger('src.peer.grpc_services')

def get_file_discovery_logger() -> logging.Logger:
    """Logger para file discovery"""
    return logging.getLogger('src.peer.file_discovery')

def get_peer_manager_logger() -> logging.Logger:
    """Logger para peer manager"""
    return logging.getLogger('src.peer.peer_manager')
