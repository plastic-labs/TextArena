import textarena as ta
import fantasynames as names
import random
from typing import Union, Tuple
import os
import json
import argparse
from dotenv import load_dotenv

load_dotenv()

# hf_access_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
# hf_cache_dir = os.getenv("HUGGINGFACE_HUB_CACHE")
# print(f'HF Access Token: {hf_access_token}')
# print(f'HF Cache Dir: {hf_cache_dir}')

# Set Hugging Face cache directory to /raid/weights


def create_player(player_id: int, use_local_model: bool = False) -> Tuple[ta.Agent, str]:
    """
    Create a player with a random fantasy name and either Claude 3.5 Haiku or local Llama 3 model.
    
    Args:
        player_id: The ID of the player
        use_local_model: Whether to use a local Llama 3 model instead of OpenRouter
        
    Returns:
        tuple: (agent, player_name)
    """
    # Choose a random name generator
    fantasy_name_generators = [
        names.elf,
        names.dwarf,
        names.hobbit,
        names.french,
        names.anglo,
        names.human
    ]
    name_generator = random.choice(fantasy_name_generators)
    agent_name = name_generator()
    
    if use_local_model:
        # Create the agent with Llama 3 8B-Instruct from Hugging Face
        agent = ta.agents.HFLocalAgent(
            model_name="meta-llama/Llama-3.2-3B-Instruct",
            device="cuda",  # or "cpu" if no GPU available
            quantize=True  # Use 8-bit quantization to reduce memory usage
        )
    else:
        # Create the agent with Claude 3.5 Haiku
        # agent = ta.agents.OpenRouterAgent(model_name="meta-llama/llama-3.3-70b-instruct")
        agent  = ta.agents.AnthropicAgent(model_name="claude-3-5-haiku-latest")
    
    player_name = f"{agent_name}"
    
    return agent, player_name

def main(await_input: bool = False):
    # Create 5 players
    agents = {}
    player_names = {}
    n_players = 6
    
    # Create 4 players with OpenRouter and 1 with local model
    for i in range(n_players):
        use_local_model = False
        agent, player_name = create_player(i, use_local_model)
        agents[i] = agent
        player_names[i] = player_name

    # Initialize environment from subset and wrap it
    env = ta.make(env_id="SecretMafia-v0", mafia_ratio=0.25, discussion_rounds=3)
    env = ta.wrappers.LLMObservationWrapper(env=env)
    env = ta.wrappers.SimpleRenderWrapper(
        env=env,
        player_names=player_names,
    )

    # Reset environment with 5 players
    env.reset(num_players=n_players)
    env = ta.wrappers.CSVLoggerWrapper(env=env, log_dir="outputs/mafia_logs")  # Add CSV logger
    
    # Main game loop
    done = False
    while not done:
        player_id, observation = env.get_observation()
        action = agents[player_id](observation)
        step_result = env.step(action=action)
        done = step_result[0]  # First element is the done flag
        if await_input:
            input("Press Enter to continue...")
    
    # Get final rewards
    rewards = env.close()
    print("Game Over!")
    print(f"Final rewards: {rewards}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--await_input", type=bool, default=False)
    args = parser.parse_args()
    main(await_input=args.await_input)
