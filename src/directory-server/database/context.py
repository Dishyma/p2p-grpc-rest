# src/shared/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import os
from ...shared.database.models import Base

class DatabaseConnection:
    def __init__(self):
        db_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:password@localhost:5432/p2p_directory"
        )
        
        self.engine = create_engine(
            db_url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_pre_ping=True
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Crea todas las tablas en la base de datos"""
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager para manejo de sesiones"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Instancia global
db_connection = DatabaseConnection()

def get_db_session() -> Session:
    """Para dependency injection en FastAPI"""
    return db_connection.SessionLocal()