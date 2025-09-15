from abc import ABC, abstractmethod
from typing import List, Optional, Generic, TypeVar

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository con operaciones CRUD básicas"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_all(self) -> List[T]:
        pass
