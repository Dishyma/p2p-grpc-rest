from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from ..models.peer import PeerModel

class IPeerRepository(ABC):
    @abstractmethod
    def create(self, peer: PeerModel) -> PeerModel:
        pass
    
    @abstractmethod
    def get_by_id(self, peer_id: UUID) -> Optional[PeerModel]:
        pass
    
    @abstractmethod
    def get_all_active(self) -> List[PeerModel]:
        pass
    
    @abstractmethod
    def update(self, peer: PeerModel) -> PeerModel:
        pass
    
    @abstractmethod
    def delete(self, peer_id: UUID) -> bool:
        pass
    
    @abstractmethod
    def update_heartbeat(self, peer_id: UUID) -> bool:
        pass
