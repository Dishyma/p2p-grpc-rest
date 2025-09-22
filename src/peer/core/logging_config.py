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
    
    log_dir = Path("logs/peer")
    log_dir.mkdir(parents=True, exist_ok=True)
    
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
            'src.peer': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            'src.peer.grpc_services': {
                'level': 'DEBUG',
                'handlers': ['file_grpc', 'file_error'],
                'propagate': False
            },
            'src.peer.api_server': {
                'level': 'DEBUG',
                'handlers': ['file_api', 'file_error'],
                'propagate': False
            },
            'src.peer.file_discovery': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            'src.peer.peer_manager': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
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
    
    logging.config.dictConfig(logging_config)
    
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
