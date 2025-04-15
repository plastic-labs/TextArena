from ..base import MemoryStrategy
from textarena.agents import Agent
from honcho import Honcho

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
            metamessages = self.honcho.apps.users.metamessages.list(
                app_id=self.app.id,
                user_id=self.user.id,
                session_id=self.session.id,
                message_id=msg.id,
                metamessage_type="private_thought"
            )
            
            # Add private thoughts if any
            for meta in metamessages:
                context += f"  (Private thought): {meta.content}\n"
        
        # Combine with current observation
        pre_rumination_context = f"{context}\nCurrent observation:\n{observation}"
        
        # Generate private thought
        private_thought = self.ruminate(pre_rumination_context)
        
        # Store the private thought for use in process_action
        self._store("private_thought", private_thought)

        # Return the augmented observation
        return f"{pre_rumination_context}\n\n{private_thought}"

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
        return self.base_agent(private_prompt)

    def process_action(self, action: str) -> None:
        """Process and store the action with its private thought."""
        # Write the action message
        message = self.honcho.apps.users.sessions.messages.create(
            app_id=self.app.id,
            user_id=self.user.id,
            session_id=self.session.id,
            content=action,
            is_user=True
        )
        
        # Get the stored private thought
        if private_thought := self._get("private_thought"):
            # Write the private thought as a metamessage
            self.honcho.apps.users.metamessages.create(
                app_id=self.app.id,
                user_id=self.user.id,
                session_id=self.session.id,
                message_id=message.id,
                content=private_thought,
                metamessage_type="private_thought"
            )
        
        # Context is automatically cleared by the base class
    