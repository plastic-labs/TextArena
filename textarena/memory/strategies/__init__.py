from typing import Type, Dict
from ..base import MemoryStrategy

# Import all strategy implementations
from .mafia import MafiaMemoryStrategy

# Registry of available memory strategies
STRATEGIES: Dict[str, Type[MemoryStrategy]] = {
    'mafia': MafiaMemoryStrategy,
}

def get_strategy(game_type: str) -> Type[MemoryStrategy]:
    """
    Get the appropriate memory strategy class for a game type.
    
    Args:
        game_type (str): Type of game to get strategy for
        
    Returns:
        Type[MemoryStrategy]: Memory strategy class for the game type
        
    Raises:
        ValueError: If no strategy is found for the game type
    """
    if game_type not in STRATEGIES:
        raise ValueError(f"No memory strategy found for game type: {game_type}")
    return STRATEGIES[game_type]

__all__ = [
    'MemoryStrategy',
    'MafiaMemoryStrategy',
    'get_strategy',
]
