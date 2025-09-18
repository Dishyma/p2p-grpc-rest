from functools import lru_cache
from sqlalchemy.orm import Session
from fastapi import Depends
from ..contextdb.connection import get_db_session
from ..repositories.peer_repository import PeerRepository
from ..repositories.file_repository import PeerFileRepository
from ..services.directory_service import DirectoryService

def get_peer_repository(db: Session = Depends(get_db_session)) -> PeerRepository:
    return PeerRepository(db)

def get_file_repository(db: Session = Depends(get_db_session)) -> PeerFileRepository:
    return PeerFileRepository(db)

def get_directory_service(
    peer_repo: PeerRepository = Depends(get_peer_repository),
    file_repo: PeerFileRepository = Depends(get_file_repository)
) -> DirectoryService:
    return DirectoryService(peer_repo, file_repo)
