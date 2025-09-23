from .peers import router as peers_router
from .health import router as health_router
from .auth import router as auth_router

__all__ = ["peers_router", "health_router", "auth_router"]
