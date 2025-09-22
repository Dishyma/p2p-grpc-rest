from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import sys

from .config import config
from .contextdb.connection import db_connection
from .api.v1.routers import peers_router, health_router, auth_router
from .logging_config import setup_directory_logging, get_logger

# Configurar logging profesional
logger = setup_directory_logging(config.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    # Startup
    logger.info("Starting directory server")
    
    # Crear tablas de base de datos
    try:
        db_connection.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down directory server...")

# Crear aplicación FastAPI
app = FastAPI(
    title=config.app_title,
    description=config.app_description,
    version=config.app_version,
    lifespan=lifespan
)

# Incluir routers
app.include_router(auth_router, prefix=config.api_prefix)
app.include_router(peers_router, prefix=config.api_prefix)
app.include_router(health_router, prefix=config.api_prefix)

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": config.app_title,
        "version": config.app_version,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.reload
    )