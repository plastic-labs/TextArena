from .strategies.mafia import MafiaMemoryStrategy

STRATEGIES = {
    'mafia': MafiaMemoryStrategy,
}

def get_strategy(game_type: str):
    """Get the appropriate memory strategy for a game type."""
    if game_type not in STRATEGIES:
        raise ValueError(f"No memory strategy found for game type: {game_type}")
    return STRATEGIES[game_type]
