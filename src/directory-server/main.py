from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
import sys

from .config import config
from .contextdb.connection import db_connection
from .api.v1.routers import peers_router, health_router, auth_router
from .logging_config import setup_directory_logging, get_logger

logger = setup_directory_logging(config.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    logger.info("Starting directory server")
    
    try:
        db_connection.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise
    
    yield
    
    logger.info("Shutting down directory server...")

app = FastAPI(
    title=config.app_title,
    description=config.app_description,
    version=config.app_version,
    lifespan=lifespan
)

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