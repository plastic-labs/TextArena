from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from honcho import Honcho

class MemoryStrategy(ABC):
    """Base class for game-specific memory strategies."""
    
    def __init__(self, honcho: Honcho, app, user, session):
        self.honcho = honcho
        self.app = app
        self.user = user
        self.session = session
        self._context: Dict[str, Any] = {}
        
    def _store(self, key: str, value: Any) -> None:
        """Store context for use in process_action."""
        self._context[key] = value
        
    def _get(self, key: str) -> Optional[Any]:
        """Get stored context."""
        return self._context.get(key)
        
    @abstractmethod
    def process_observation(self, observation: str) -> str:
        """
        Process observation with historical context.
        
        This method should:
        1. Process the observation and generate any necessary context
        2. Store context using _store if needed
        3. Return the augmented observation string
        """
        pass
        
    @abstractmethod
    def process_action(self, action: str) -> None:
        """
        Process and store an action with any associated context.
        
        This method should:
        1. Use any stored context from process_observation
        2. Write messages and metamessages as needed
        3. Clear context after processing
        """
        self._context.clear()  # Always clear context after processing