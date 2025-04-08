from ..base import MemoryStrategy
from textarena.agents import Agent

class MafiaMemoryStrategy(MemoryStrategy):
    def __init__(self, honcho: Honcho, app, user, session, base_agent: Agent):
        super().__init__(honcho, app, user, session)
        self.base_agent = base_agent

    def process_observation(self, observation: str) -> str:
        """Process observation with historical context."""
        # Get all messages from this session
        messages = self.honcho.apps.users.sessions.messages.list(
            app_id=self.app.id,
            user_id=self.user.id,
            session_id=self.session.id
        )
        
        # Format historical context
        context = "\nPrevious messages:\n"
        for msg in messages:
            sender = "Game" if msg.is_user else "Player"
            context += f"{sender}: {msg.content}\n"
            
            # Get metamessages for this message
            metamessages = self.honcho.apps.users.sessions.messages.metamessages.list(
                app_id=self.app.id,
                user_id=self.user.id,
                session_id=self.session.id,
                message_id=msg.id
            )
            
            # Add private thoughts if any
            for meta in metamessages:
                context += f"  (Private thought): {meta.content}\n"
        
        # Combine with current observation
        return f"{context}\nCurrent observation:\n{observation}"

    def ruminate(self, observation: str) -> str:
        """Let the agent think privately about the observation."""
        # Create a prompt for private thinking
        private_prompt = (
            f"You are playing Mafia. This is your private thinking space - no one else can see these thoughts.\n"
            f"Consider the following carefully:\n"
            f"1. What is your role? What are your goals?\n"
            f"2. What information do you have about other players?\n"
            f"3. What strategies could you use to achieve your goals?\n"
            f"4. What should you say or do next?\n\n"
            f"Current situation:\n{observation}\n\n"
            f"Think through your strategy and what you should say next. Be strategic and consider your role."
        )
        
        # Get private thoughts from the base agent
        private_thought = self.base_agent(private_prompt)
        
        # Create a private thought message
        thought = self.honcho.apps.users.sessions.messages.create(
            app_id=self.app.id,
            user_id=self.user.id,
            session_id=self.session.id,
            content=private_thought,
            is_user=True
        )
        
        # Add a metamessage with the private thought
        self.honcho.apps.users.sessions.messages.metamessages.create(
            app_id=self.app.id,
            user_id=self.user.id,
            session_id=self.session.id,
            message_id=thought.id,
            content=private_thought
        )
        
        return private_thought
    