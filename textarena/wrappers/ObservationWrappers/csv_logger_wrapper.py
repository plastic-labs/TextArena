import textarena as ta
from textarena.core import ObservationWrapper, Env
import csv
from datetime import datetime
import os
from typing import Dict, Optional, Tuple, List, Any

class CSVLoggerWrapper(ObservationWrapper):
    """
    A wrapper that logs all observations to a CSV file.
    Each observation is logged with timestamp, from_id, to_id, and message.
    """
    
    def __init__(self, env: Env, log_dir: str = "logs"):
        """
        Initialize the CSVLoggerWrapper.
        
        Args:
            env (Env): The environment to wrap
            log_dir (str): Directory to store log files
        """
        super().__init__(env)
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a unique log file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"observations_{timestamp}.csv")
        
        # Initialize CSV file with headers
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'from_id', 'to_id', 'message'])
    
    def _log_observation(self, from_id: int, to_id: int, message: str):
        """Helper method to log an observation to CSV"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, from_id, to_id, message])
    
    def _wrapped_add_observation(self, from_id: int, to_id: int, message: str, for_logging: bool = True):
        """
        Wrapped version of state.add_observation that logs to CSV before calling the original method.
        """
        # Log to CSV
        self._log_observation(from_id=from_id, to_id=to_id, message=message)
        
        # Call the original method
        return self.original_add_observation(from_id=from_id, to_id=to_id, message=message, for_logging=for_logging)
    
    def observation(self, player_id: int, observation: Optional[ta.Observations]):
        """
        Process observations from the environment.
        This method is required by ObservationWrapper but we don't need to modify observations.
        """
        return observation

    def reset(self, **kwargs):
        """
        Reset the environment and log the reset event.
        """
        self.env.reset(**kwargs)
        # Store the original add_observation method
        self.original_add_observation = self.env.state.add_observation
        
        # Override the state's add_observation method
        self.env.state.add_observation = self._wrapped_add_observation
