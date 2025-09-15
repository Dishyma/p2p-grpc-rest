from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
from ..shared.loggin import configure_logging, get_logger
from ..shared.database.connection import db_connection
from .api.v1.routers import peers_router, health_router

# Configurar logging
configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    # Startup
    logger.info("Starting directory server...")
    
    # Crear tablas de base de datos
    try:
        db_connection.create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down directory server...")

# Crear aplicación FastAPI
app = FastAPI(
    title="P2P Directory Server",
    description="Servidor de directorio para red P2P",
    version="1.0.0",
    lifespan=lifespan
)

# Incluir routers
app.include_router(peers_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "P2P Directory Server",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development"
    )