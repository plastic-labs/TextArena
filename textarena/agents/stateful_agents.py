from typing import Type, Optional
from honcho import Honcho
from uuid import uuid4
from .basic_agents import Agent  # Import base Agent class

class HonchoAgent(Agent):
    """A wrapper that adds stateful memory to any TextArena agent using Honcho."""
    
    def __init__(self, base_agent: Agent, game_type: str, session=None):
        """
        Initialize a stateful agent wrapper.
        
        Args:
            base_agent (Agent): Any TextArena agent to make stateful
            game_type (str): Type of game for organizing memory
            session: Optional existing Honcho session to use
        """
        super().__init__()
        self.base_agent = base_agent
        self.game_type = game_type
        
        # Initialize Honcho client
        self.honcho = Honcho()
        self.app = self.honcho.apps.get_or_create(name=f"TextArena-{game_type}")
        
        # Create unique ID for this agent instance
        self.agent_id = str(uuid4())
        self.user = self.honcho.apps.users.get_or_create(
            app_id=self.app.id, 
            name=self.agent_id
        )
        
        # Store session if provided, otherwise it will be created when needed
        self._session = session
        self.memory_strategy = None  # Will be initialized when session is available

    def start_game(self):
        """Start a new game session."""
        if self._session is None:
            self._session = self.honcho.apps.users.sessions.create(
                app_id=self.app.id,
                user_id=self.user.id
            )
        self.memory_strategy = self._get_memory_strategy(self.game_type)

    def _get_memory_strategy(self, game_type: str):
        """Get the appropriate memory strategy for this game type."""
        from textarena.memory.strategies import get_strategy
        return get_strategy(game_type)(self.honcho, self.app, self.user, self._session, self.base_agent)

    def __call__(self, observation: str) -> str:
        """
        Process observation with historical context and return action.
        
        Args:
            observation (str): Current game observation
            
        Returns:
            str: Agent's action
            
        Raises:
            RuntimeError: If game session has not been started
        """
        if self.memory_strategy is None:
            raise RuntimeError("Game session not started. Call start_game() first.")
            
        # Get augmented observation from memory strategy
        augmented_obs = self.memory_strategy.process_observation(observation)
        
        # Let the agent think privately about the observation
        private_thought = self.memory_strategy.ruminate(augmented_obs)
        
        # Get final action from base agent
        action = self.base_agent(private_thought)
        
        return action 