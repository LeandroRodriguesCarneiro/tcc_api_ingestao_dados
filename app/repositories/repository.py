from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

class Repository(ABC):
    def __init__(self, session: Session):
        self.session = session

    @abstractmethod
    def add(self):
        pass
    
    @abstractmethod
    def get_by_id(self):
        pass

    @abstractmethod
    def get_all(self):
        pass
    
    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def update(self):
        pass