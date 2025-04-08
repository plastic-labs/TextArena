import textarena as ta
from dotenv import load_dotenv

load_dotenv()

# Initialize agents
agents = {
    0: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="GPT-4o-mini"),
        game_type="mafia"
    ),
    1: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="anthropic/claude-3.5-haiku"),
        game_type="mafia"
    ),
    2: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="anthropic/claude-3.5-haiku"),
        game_type="mafia"
    ),
    3: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="anthropic/claude-3.5-haiku"),
        game_type="mafia"
    ),
    4: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="anthropic/claude-3.5-haiku"),
        game_type="mafia"
    ),
    5: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="anthropic/claude-3.5-haiku"),
        game_type="mafia"
    ),
    6: ta.agents.HonchoAgent(
        base_agent=ta.agents.OpenRouterAgent(model_name="anthropic/claude-3.5-haiku"),
        game_type="mafia"
    ),
}
# Play multiple games
num_games = 3
for game_num in range(num_games):
    print(f"\nStarting game {game_num + 1}")
    
    # Start new sessions for this game
    for agent in agents.values():
        agent.start_game()
    
    # Initialize environment from subset and wrap it
    env = ta.make(env_id="SecretMafia-v0")
    env = ta.wrappers.LLMObservationWrapper(env=env)
    env = ta.wrappers.SimpleRenderWrapper(
        env=env,
        player_names={
            0: "GPT-4o-mini", 
            1: "claude-3.5-haiku", 
            2: "claude-3.5-haiku", 
            3: "claude-3.5-haiku", 
            4: "claude-3.5-haiku", 
            5: "claude-3.5-haiku", 
            6: "claude-3.5-haiku"
        },
    )
    
    env.reset(num_players=len(agents))
    done = False
    while not done:
        player_id, observation = env.get_observation()
        action = agents[player_id](observation)
        done, info = env.step(action=action)
    rewards = env.close()
    print(f"Game {game_num + 1} completed!")