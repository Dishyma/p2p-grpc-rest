"""
Configuración de logging profesional para el Directory Server
"""
import logging
import logging.config
import os
from pathlib import Path

def setup_directory_logging(log_level: str = "INFO"):
    """
    Configura el sistema de logging para el directory server
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    log_dir = Path("logs/directory")
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
            'access': {
                'format': '%(asctime)s - %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
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
                'filename': 'logs/directory/directory_server.log',
                'maxBytes': 10485760,
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': 'logs/directory/directory_error.log',
                'maxBytes': 10485760,
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_api': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': 'logs/directory/api_requests.log',
                'maxBytes': 10485760,
                'backupCount': 3,
                'encoding': 'utf8'
            },
            'file_auth': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filename': 'logs/directory/auth.log',
                'maxBytes': 5242880,
                'backupCount': 3,
                'encoding': 'utf8'
            },
            'file_database': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'logs/directory/database.log',
                'maxBytes': 10485760,
                'backupCount': 3,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            'src.directory-server': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            'src.directory-server.api': {
                'level': 'DEBUG',
                'handlers': ['file_api', 'file_error'],
                'propagate': False
            },
            'src.directory-server.services.auth_service': {
                'level': 'DEBUG',
                'handlers': ['file_auth', 'file_error'],
                'propagate': False
            },
            'src.directory-server.services.directory_service': {
                'level': 'DEBUG',
                'handlers': ['console', 'file_all', 'file_error'],
                'propagate': False
            },
            'src.directory-server.repositories': {
                'level': 'DEBUG',
                'handlers': ['file_database', 'file_error'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['file_api'],
                'propagate': False
            },
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': ['file_database'],
                'propagate': False
            },
            'sqlalchemy.engine': {
                'level': 'WARNING',
                'handlers': ['file_database'],
                'propagate': False
            },
            'alembic': {
                'level': 'INFO',
                'handlers': ['file_database'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    logger = logging.getLogger('src.directory-server')
    logger.info("Directory Server logging system initialized")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log directory: {log_dir.absolute()}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado
    
    Args:
        name: Nombre del logger (ej: 'src.directory-server.api')
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)

def get_api_logger() -> logging.Logger:
    """Logger para API routes"""
    return logging.getLogger('src.directory-server.api')

def get_auth_logger() -> logging.Logger:
    """Logger para autenticación"""
    return logging.getLogger('src.directory-server.services.auth_service')

def get_directory_service_logger() -> logging.Logger:
    """Logger para servicios de directorio"""
    return logging.getLogger('src.directory-server.services.directory_service')

def get_database_logger() -> logging.Logger:
    """Logger para operaciones de base de datos"""
    return logging.getLogger('src.directory-server.repositories')
