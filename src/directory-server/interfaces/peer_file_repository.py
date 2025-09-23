from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from ..models.peer_file import PeerFileModel

class IPeerFileRepository(ABC):
    @abstractmethod
    def create(self, peer_file: PeerFileModel) -> PeerFileModel:
        pass
    
    @abstractmethod
    def get_by_id(self, file_id: UUID) -> Optional[PeerFileModel]:
        pass
    
    @abstractmethod
    def get_by_peer_id(self, peer_id: UUID) -> List[PeerFileModel]:
        pass
    
    @abstractmethod
    def search_by_filename(self, filename: str) -> List[PeerFileModel]:
        pass
    
    @abstractmethod
    def update(self, peer_file: PeerFileModel) -> PeerFileModel:
        pass
    
    @abstractmethod
    def delete(self, file_id: UUID) -> bool:
        pass
    
    @abstractmethod
    def delete_by_peer_id(self, peer_id: UUID) -> bool:
        pass
