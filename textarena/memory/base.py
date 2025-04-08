from abc import ABC, abstractmethod
from typing import Dict, Any
from honcho import Honcho

class MemoryStrategy(ABC):
    """Base class for game-specific memory strategies."""
    
    def __init__(self, honcho: Honcho, app, user, session):
        self.honcho = honcho
        self.app = app
        self.user = user
        self.session = session
        
    @abstractmethod
    def process_observation(self, observation: str) -> str:
        """Process observation with historical context."""
        pass