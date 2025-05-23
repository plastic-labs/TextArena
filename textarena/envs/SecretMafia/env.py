import re, random
from typing import Any, Dict, Optional, Tuple, List, Set

import textarena as ta
from textarena.utils.xml_utils import parse_xml_content, format_xml_prompt
from textarena.core import DEBUG_ID

# XML tags for different types of actions
TAG_DISCUSSION = "discussion"
TAG_VOTE = "vote"
TAG_MAFIA_VOTE = "mafia_vote"
TAG_MAFIA_SUGGEST = "mafia_suggest"
TAG_PROTECT = "protect"
TAG_INVESTIGATE = "investigate"
TAG_REFLECT = "reflect"

"""
TODO:
    - maybe it's worth adding a mafia chat?
    - is the doctor allowed to save themselves?
"""

class SecretMafiaEnv(ta.Env):
    # Message patterns for player actions
    voting_pattern = re.compile(r'.*\[(?:player\s*)?(\d+)\].*', re.IGNORECASE)

    def __init__(self, mafia_ratio: float = 0.25, discussion_rounds: int = 3):
        """
        Initialize the Secret Mafia Game environment.

        Args:
            mafia_ratio (float): Ratio of Mafia members to total players (default: 0.25)
            discussion_rounds (int): The number of discussion rounds
        """
        self.mafia_ratio = mafia_ratio
        self.discussion_rounds = discussion_rounds

        # Role definitions
        self.roles = {
            "Villager": {
                "team": "Village",
                "description": "A regular villager. Your goal is to identify and eliminate all Mafia members through voting during the day."
            },
            "Mafia": {
                "team": "Mafia",
                "description": "A Mafia member. Your goal is to eliminate enough villagers to gain majority. During the night phase, you can communicate secretly with other Mafia members and vote to eliminate a villager."
            },
            "Doctor": {
                "team": "Village",
                "description": "A villager with medical skills. During the night phase, you can choose one player to protect from Mafia elimination."
            },
            "Detective": {
                "team": "Village",
                "description": "A villager with investigative skills. During the night phase, you can investigate one player to learn if they are a Mafia member."
            }
        }

    @property
    def terminal_render_keys(self):
        return ["phase", "alive_players", "player_roles", "votes", "night_actions", "detective_inspected"]

    def reset(self, num_players: int, seed: Optional[int] = None):
        """ Reset the environment """
        self.state = ta.State(num_players=num_players, min_players=5, max_players=15, error_allowance=100)
        
        # Initialize game state
        self._assign_roles(num_players)
        self.num_discussion_rounds = 2
        
        game_state = {
            "phase": "Night-Mafia-Discussion",
            "day_number": 1,
            "alive_players": list(range(num_players)),
            "player_roles": self.player_roles,
            "votes": {},
            "to_be_eliminated": None,
            "kill_suggestions": {},
            "detective_inspected": []
        }
        
        self.state.reset(seed=seed, game_state=game_state, player_prompt_function=self._generate_player_prompt)

        # the game starts with the mafia discussion
        self._phase_transition_player_prompts(new_phase="Night-Mafia-Discussion")
        self._transition_current_pid()

    def _assign_roles(self, num_players: int):
        """
        Assign roles to players based on the number of players and mafia ratio.
        
        Args:
            num_players (int): Number of players in the game
            seed (Optional[int]): Random seed for reproducibility
        """
        self.player_roles = {}
        
        # Calculate number of mafia members
        num_mafia = max(1, round(num_players * self.mafia_ratio))
        
        # Create the role pool
        role_pool = ["Mafia"] * num_mafia + ["Doctor"] + ["Detective"]
        
        
        num_villagers = num_players - len(role_pool)
        role_pool.extend(["Villager"] * num_villagers)
        
        # Shuffle and assign roles
        random.shuffle(role_pool)
        for i in range(num_players):
            self.player_roles[i] = role_pool[i]
        

    def _generate_player_prompt(self, player_id: int, game_state: Dict[str, Any]) -> str:
        """ Generate the initial prompt for each player, including their role and objectives """
        role = game_state["player_roles"][player_id]
        role_info = self.roles[role]
        
        # Calculate list of players
        player_list = ", ".join([f"Player {i}" for i in range(self.state.num_players)])
        
        # Basic prompt for all players
        prompt = (
            f"Welcome to Secret Mafia! You are Player {player_id}.\n"
            f"Your role: {role}\n"
            f"Team: {role_info['team']}\n"
            f"Description: {role_info['description']}\n\n"
            f"Players: {player_list}\n\n"
            f"Game Overview:\n"
            f"All Roles and Their Abilities:\n"
            f"    • Villager: Regular villager with no special abilities. Goal is to identify and eliminate Mafia members.\n"
            f"    • Mafia: During the night, can secretly coordinate (without talking) with other Mafia members to eliminate a player.\n"
            f"    • Doctor: Can protect one player from elimination each night.\n"
            f"    • Detective: Can investigate one player each night: will be told whether they are Mafia.\n\n"
            f"    • Players do not know other players' roles, aside from any investigation results made by the detective.\n\n"
            f"The game starts with the Night phase, where special roles take their actions\n"
            f"    • The Mafia can coordinate (without talking) with other Mafia members and vote to eliminate a player\n"
            f"    • If there is a tie, no one is eliminated\n"
            f"    • If the Doctor chooses to save the player elected by the Mafia, the player is not eliminated\n\n"
            f"    • If the Detective investigates a player and they are Mafia, the Detective will know\n\n"
            f"During the Day phase, there are two parts:\n"
            f"  1. Private Reflection: Each player gets time to think privately about the game state\n"
            f"     - Your thoughts during this phase are NOT shared with other players\n"
            f"     - Use this time to analyze the game and plan your strategy\n"
            f"  2. Public Discussion: {self.num_discussion_rounds} rounds of open discussion\n"
            f"     - Everything you say in this phase is visible to ALL players\n"
            f"     - Be careful about what you reveal and how you present yourself\n"
            f"After discussions, all players must vote to eliminate one player\n"
            f"The game ends when either all Mafia members are eliminated (Village wins) or\n"
            f"Mafia members equal or outnumber Villagers (Mafia wins)\n\n"
        )
        
        # Add role-specific information and abilities
        if role == "Mafia":
            mafia_members = [f"Player {pid}" for pid, r in game_state["player_roles"].items() if r == "Mafia"]
            prompt += (
                f"You are part of the Mafia team. Your teammates are: {', '.join(mafia_members)}.\n\n"
                "Your abilities:\n"
                "  During DAY phase:\n"
                "    • Everything you say is automatically shared with all players\n"
                "    • You'll vote to eliminate a player at the end of discussions\n\n"
                "  During NIGHT phase:\n"
                "    • First, you'll discuss with other Mafia members about who to eliminate\n"
                "    • Then, you'll vote to eliminate a player (must be a non-Mafia player)\n"
                "    • Use the format '[Player X]' to vote\n\n"
                "Your goal is to eliminate enough villagers until Mafia members equal or outnumber the Villagers.\n\n"
            )
        elif role == "Doctor":
            prompt += (
                "Your abilities:\n"
                "  During DAY phase:\n"
                "    • Everything you say is automatically shared with all players\n"
                "    • You'll vote to eliminate a player at the end of discussions\n\n"
                "  During NIGHT phase:\n"
                "    • You can protect one player from being eliminated by the Mafia\n"
                "    • Use the format '[Player X]' to protect a player\n"
                "    • You cannot protect yourself\n\n"
                "Your goal is to help identify and eliminate all Mafia members.\n\n"
            )
        elif role == "Detective":
            prompt += (
                "Your abilities:\n"
                "  During DAY phase:\n"
                "    • Everything you say is automatically shared with all players\n"
                "    • You'll vote to eliminate a player at the end of discussions\n\n"
                "  During NIGHT phase:\n"
                "    • You can investigate one player to learn if they are Mafia\n"
                "    • Use the format '[Player X]' to investigate a player\n"
                "    • You'll receive immediate results of your investigation\n\n"
                "Your goal is to help identify and eliminate all Mafia members.\n\n"
            )
        else:  # Villager
            prompt += (
                "Your abilities:\n"
                "  During DAY phase:\n"
                "    • Everything you say is automatically shared with all players\n"
                "    • You'll vote to eliminate a player at the end of discussions\n\n"
                "  During NIGHT phase:\n"
                "    • You have no special actions during the night phase\n"
                "    • You must wait for the day phase to participate\n\n"
                "Your goal is to help identify and eliminate all Mafia members.\n\n"
            )
        
        return prompt


    def _phase_transition_player_prompts(self, new_phase):
        """ During a phase transition, provide relevant prompts to all players """
        if new_phase == "Night-Mafia-Discussion":
            # all mafia players receive a prompt to discuss their target
            mafia_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Mafia" and pid in self.state.game_state["alive_players"]]
            remaining_non_mafia = [pid for pid, role in self.state.game_state["player_roles"].items() if role!="Mafia" and pid in self.state.game_state["alive_players"]]
            valid_targets = ", ".join([f"'[{rpid}]'" for rpid in remaining_non_mafia])
            base_prompt = (
                f"The Night phase has begun. As Mafia members, you must silently coordinate your target.\n"
                f"You cannot speak or write messages - you can only point to your intended target.\n"
                f"Valid targets: {valid_targets}\n\n"
                f"Remember:\n"
                f"• You cannot write explanations or discuss\n"
                f"• You can only point to a player\n"
                f"• After this round, you will vote on the final target\n"
                f"• If you don't agree with a suggestion, you can point to a different player\n"
                f"• The player with the most suggestions will be the default target for voting\n"
                f"• If you speak out loud by saying anything other than pointing to a target, other players will hear you and know you're mafia"
            )
            mafia_discussion_prompt = format_xml_prompt(
                base_prompt=base_prompt,
                tag=TAG_MAFIA_SUGGEST,
                instruction=f"Use the format <{TAG_MAFIA_SUGGEST}>[Player X]</{TAG_MAFIA_SUGGEST}> to indicate your suggestion."
            )
            # send observations to all relevant players
            for pid in mafia_pids:
                self.state.add_observation(from_id=ta.GAME_ID, to_id=pid, message=mafia_discussion_prompt)

            # update new player orders - each mafia gets 2 turns to suggest
            random.shuffle(mafia_pids)
            self.next_player_ids = mafia_pids * 2

        elif new_phase == "Night-Mafia":
            # all mafia players receive a prompt to vote whom to kill
            mafia_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Mafia" and pid in self.state.game_state["alive_players"]]
            remaining_non_mafia = [pid for pid, role in self.state.game_state["player_roles"].items() if role!="Mafia" and pid in self.state.game_state["alive_players"]]
            valid_votes = ", ".join([f"'[{rpid}]'" for rpid in remaining_non_mafia])
            base_prompt = (
                f"The voting phase has begun. Please vote who you would like to kill. "
                f"Valid votes: {valid_votes}"
            )
            mafia_observation = format_xml_prompt(
                base_prompt=base_prompt,
                tag=TAG_MAFIA_VOTE,
                instruction=f"Use the format <{TAG_MAFIA_VOTE}>[Player X]</{TAG_MAFIA_VOTE}> to cast your vote. Do not include any other text."
            )
            # send observations to all relevant players
            for pid in mafia_pids:
                self.state.add_observation(from_id=ta.GAME_ID, to_id=pid, message=mafia_observation)

            # update new player orders
            self.next_player_ids = mafia_pids
            random.shuffle(self.next_player_ids)

        elif new_phase == "Night-Doctor":
            # get doctor pid 
            d_pid = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Doctor"][0]
            valid_player_options = [pid for pid, role in self.state.game_state["player_roles"].items() if role!="Doctor" and pid in self.state.game_state["alive_players"]]
            
            # check if doctor is still alive
            # if d_pid in self.state.game_state["alive_players"]:
            valid_options = ", ".join([f"'[{rpid}]'" for rpid in valid_player_options])
            base_prompt = (
                f"We are in the Night phase. Since you are the doctor, you can decide which player to save."
                f"Valid options: {valid_options}"
            )
            doctor_observation = format_xml_prompt(
                base_prompt=base_prompt,
                tag=TAG_PROTECT,
                instruction=f"Use the format <{TAG_PROTECT}>[Player X]</{TAG_PROTECT}> to protect a player."
            )
            self.state.add_observation(from_id=ta.GAME_ID, to_id=d_pid, message=doctor_observation)

            self.next_player_ids = [d_pid]

        elif new_phase == "Night-Detective":
            # get detective pid 
            d_pid = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Detective"][0]
            valid_player_options = [pid for pid, role in self.state.game_state["player_roles"].items() if role!="Detective" and pid in self.state.game_state["alive_players"]]
            
            # check if detective is still alive 
            if d_pid in self.state.game_state["alive_players"]:
                valid_options = ", ".join([f"'[{rpid}]'" for rpid in valid_player_options])
                base_prompt = (
                    f"We are in the Night phase. Since you are the detective, you can decide which player to investigate."
                    f"Valid options: {valid_options}"
                )
                detective_observation = format_xml_prompt(
                    base_prompt=base_prompt,
                    tag=TAG_INVESTIGATE,
                    instruction=f"Use the format <{TAG_INVESTIGATE}>[Player X]</{TAG_INVESTIGATE}> to investigate a player."
                )
                self.state.add_observation(from_id=ta.GAME_ID, to_id=d_pid, message=detective_observation)
                self.next_player_ids = [d_pid]

        elif new_phase == "Day-Private-Reflection":
            # First send private reflection prompt to each player
            for pid in self.state.game_state["alive_players"]:
                role = self.state.game_state["player_roles"][pid]
                reflection_prompt = (
                    f"Take a moment to reflect privately:\n\n"
                    f"1. Current State & Position:\n"
                    f"   - What is your current role and position in the game?\n"
                    f"   - What are your immediate goals and concerns?\n"
                    f"   - What can you do to help your team win?\n\n"
                    f"2. Player Analysis. For each other player:\n"
                    f"   - Analyze their behavior and decisions so far\n"
                    f"   - Consider their voting patterns and discussion contributions\n"
                    f"   - Note any suspicious patterns or inconsistencies\n"
                    f"   - If you are a villager, do you suspect them?\n\n"
                    f"3. Perception Check. For each other player:\n"
                    f"   - How do you think they perceive you?\n"
                    f"   - If you are mafia, do you think they suspect you?\n"
                    f"   - How can you maintain or change their perception?\n\n"
                    f"Take your time to think through these points carefully."
                )
                reflection_observation = format_xml_prompt(
                    base_prompt=reflection_prompt,
                    tag=TAG_REFLECT,
                    instruction=f"Use the format <{TAG_REFLECT}>Your reflection here</{TAG_REFLECT}> to record your thoughts."
                )
                self.state.add_observation(from_id=ta.GAME_ID, to_id=pid, message=reflection_observation)

            # Set up player order for reflection
            next_players = self.state.game_state["alive_players"].copy()
            random.shuffle(next_players)
            self.next_player_ids = next_players

        elif new_phase == "Day-Discussion":
            # Send public discussion prompt
            base_prompt = (
                f"PUBLIC DISCUSSION PHASE - ALL MESSAGES WILL BE SEEN BY EVERYONE\n\n"
                f"IMPORTANT: Everything you say in this phase will be visible to ALL players.\n"
                f"Be careful about what you reveal and how you present yourself.\n"
                f"Remember that other players will analyze your words and behavior.\n\n"
                f"For the next {self.num_discussion_rounds} rounds, you can converse "
                f"freely with the other players to decide who you ultimately want to vote out.\n\n"
                f"Each player will have {self.num_discussion_rounds} turns to discuss.\n"
                f"The order of discussion will be randomized."
            )
            discussion_observation = format_xml_prompt(
                base_prompt=base_prompt,
                tag=TAG_DISCUSSION,
                instruction=f"Use the format <{TAG_DISCUSSION}>Your message here</{TAG_DISCUSSION}> to participate in the discussion."
            )
            self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=discussion_observation)
            next_players = self.state.game_state["alive_players"].copy()
            random.shuffle(next_players)
            self.next_player_ids = next_players * self.num_discussion_rounds

        elif new_phase == "Day-Voting":
            valid_options = ", ".join([f"'[{rpid}]'" for rpid in self.state.game_state['alive_players']])
            base_prompt = (
                f"The voting phase has began. On your turn, submit your vote for which player you want to vote out."
                f"Valid options: {valid_options}"
            )
            voting_observation = format_xml_prompt(
                base_prompt=base_prompt,
                tag=TAG_VOTE,
                instruction=f"Use the format <{TAG_VOTE}>[Player X]</{TAG_VOTE}> to cast your vote."
            )
            self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=voting_observation)
            self.next_player_ids = self.state.game_state["alive_players"].copy()
            random.shuffle(self.next_player_ids)
        else:
            raise Exception(f"{new_phase} phase not recognized.")


    def _transition_current_pid(self):
        """ this should iterate over the pids to call, then if empty, update the phase and call the phase transition 
        prompt function """
        # only transition if not invalid move 
        if self.state.prevent_player_change:
            return

        # check if list is empty 
        if not self.next_player_ids:
            # transition phase and replenish list
            current_phase = self.state.game_state["phase"]
            doctor_pid = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Doctor"][0]
            detective_pid = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Detective"][0]
            
            # Determine next phase based on current phase
            if current_phase == "Night-Mafia-Discussion":
                new_phase = "Night-Mafia"
            elif current_phase == "Night-Mafia":
                # check if doctor is still alive
                if doctor_pid in self.state.game_state["alive_players"]:
                    # transition to doctor phase
                    new_phase = "Night-Doctor"
                elif detective_pid in self.state.game_state["alive_players"]:
                    new_phase = "Night-Detective"
                else:
                    new_phase = "Day-Private-Reflection"
            elif current_phase == "Night-Doctor":
                if detective_pid in self.state.game_state["alive_players"]:
                    new_phase = "Night-Detective"
                else:
                    new_phase = "Day-Private-Reflection"
            elif current_phase == "Night-Detective":
                new_phase = "Day-Private-Reflection"
            elif current_phase == "Day-Private-Reflection":
                new_phase = "Day-Discussion"
            elif current_phase == "Day-Discussion":
                new_phase = "Day-Voting"
            elif current_phase == "Day-Voting":
                new_phase = "Night-Mafia-Discussion"
            else:
                # Fallback for any unexpected phase
                new_phase = "Day-Private-Reflection"

            
            # Process eliminations only at specific destination phases
            if new_phase == "Day-Private-Reflection" and current_phase != "Day-Private-Reflection":
                # Process night elimination (from Mafia kill) before Day-Private-Reflection
                tbe_pid = None
                tbe_pid = self.state.game_state["to_be_eliminated"]
                if tbe_pid is None:
                    observation = f"No player has been eliminated during the night."
                else:
                    observation = f"Player {tbe_pid} has been eliminated during the night."
                    # Remove player from alive_players
                    if tbe_pid in self.state.game_state["alive_players"]:
                        self.state.game_state["alive_players"].remove(tbe_pid)
                self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=observation)
                
                # Reset votes and to_be_eliminated
                self.state.game_state["votes"] = {}
                self.state.game_state["to_be_eliminated"] = None
                
                # Check winning conditions
                self._check_winning_conditions()
            
            elif new_phase == "Night-Mafia-Discussion" and current_phase != "Night-Mafia-Discussion":
                # Process day elimination (from voting) before Night-Mafia-Discussion
                tbe_pid = None
                tbe_pid = self.state.game_state["to_be_eliminated"]
                if tbe_pid is None:
                    observation = f"No player has been eliminated after voting."
                else:
                    observation = f"Player {tbe_pid} has been eliminated after voting."
                    # Remove player from alive_players
                    if tbe_pid in self.state.game_state["alive_players"]:
                        self.state.game_state["alive_players"].remove(tbe_pid)
                self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=observation)
                
                # Reset votes and to_be_eliminated
                self.state.game_state["votes"] = {}
                self.state.game_state["to_be_eliminated"] = None
                
                # Check winning conditions
                self._check_winning_conditions()

            # Update the game phase and prepare for the next phase
            self.state.game_state["phase"] = new_phase
            self._phase_transition_player_prompts(new_phase=new_phase)

        if not self.next_player_ids:
            self._transition_current_pid()
        else:
            # pop next pid and update state
            next_pid = self.next_player_ids.pop()
            self.state.manually_update_current_player(new_player_id=next_pid)


    def _check_winning_conditions(self):
        """ Check if the game has been won by either team """
        # winning condition 1, all mafia members are eliminated
        alive_mafia_members = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Mafia" and pid in self.state.game_state["alive_players"]]

        if not alive_mafia_members:
            # villagers win
            villager_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role!="Mafia"]
            reason = f"The villagers win by eliminating all members of the mafia."
            self.state.set_winners(player_ids=villager_pids, reason=reason)

        if len(alive_mafia_members) >= len(self.state.game_state["alive_players"])/2:
            # mafia wins
            mafia_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Mafia"]
            reason = f"The Mafia wins by outnumbering the villagers"
            self.state.set_winners(player_ids=mafia_pids, reason=reason)


    def step(self, action: str) -> Tuple[bool, ta.Info]:
        """ Process a single step (action) from the current player """
        current_pid = self.state.current_player_id

        # check game phase 
        if self.state.game_state["phase"] == "Night-Mafia-Discussion":
            self._night_mafia_discussion(current_pid=current_pid, action=action)
        elif self.state.game_state["phase"] == "Day-Private-Reflection":
            self._day_private_reflection(current_pid=current_pid, action=action)
        elif self.state.game_state["phase"] == "Day-Discussion":
            self._day_discussion(current_pid=current_pid, action=action)

        elif self.state.game_state["phase"] == "Day-Voting":
            self._day_voting(current_pid=current_pid, action=action)

        elif self.state.game_state["phase"] == "Night-Mafia":
            # game starts here. During night phase, each player votes
            self._night_mafia(current_pid=current_pid, action=action) 

        elif self.state.game_state["phase"] == "Night-Doctor":
            self._night_doctor(current_pid=current_pid, action=action)

        elif self.state.game_state["phase"] == "Night-Detective":
            self._night_detective(current_pid=current_pid, action=action)

        else:
            raise

        # rotate players
        self._transition_current_pid()

        return self.state.step(rotate_player=False)


    def _evaluate_votes(self):
        """ returns pid with most votes or None & resets the votes"""
        # Count votes for each player
        vote_counts = {}
        for voter, target in self.state.game_state["votes"].items():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        if not vote_counts:
            return None

        # Find player(s) with most votes
        max_votes = max(vote_counts.values())
        top_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
        

        # If there's a tie (more than one player with the most votes), return None
        if len(top_candidates) > 1:
            return None
        else:
            return top_candidates[0]

    def _day_private_reflection(self, current_pid, action):
        """ Handle private reflection - messages are only sent to the player themselves """
        content = parse_xml_content(action, TAG_REFLECT, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_REFLECT}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid reflection action: {action}")
            return
        self.state.add_observation(from_id=current_pid, to_id=current_pid, message=content)

    def _day_discussion(self, current_pid, action):
        """ Handle public discussion - all messages are broadcast to everyone """
        content = parse_xml_content(action, TAG_DISCUSSION, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_DISCUSSION}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid discussion action: {action}")
            return
        self.state.add_observation(from_id=current_pid, to_id=-1, message=content)

    def _day_voting(self, current_pid, action):
        """ validate voting and add to votes until no next pid """
        content = parse_xml_content(action, TAG_VOTE, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_VOTE}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid vote action: {action}")
            return
            
        # extract and validate vote 
        match = self.voting_pattern.search(content)
        if not match:
            self.state.set_invalid_move(player_id=current_pid, reason=f"The vote was not submitted in the correct format.")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid vote format: {action}")
            return
        
        voted_pid = int(match.group(1))
        # count vote
        if self.state.game_state is not None:
            if "votes" not in self.state.game_state:
                self.state.game_state["votes"] = {}
            self.state.game_state["votes"][current_pid] = voted_pid

        # check if everybody has voted
        if not self.next_player_ids:
            # evaluate votes
            if self.state.game_state is not None and "votes" in self.state.game_state:
                self.state.game_state["to_be_eliminated"] = self._evaluate_votes()
                
                # Broadcast all votes at once
                vote_summary = "[GAME] Voting Results:\n"
                for voter, target in self.state.game_state["votes"].items():
                    vote_summary += f"- Player {voter} voted for Player {target}\n"
                self.state.add_observation(from_id=ta.GAME_ID, to_id=-1, message=vote_summary)

    def _night_mafia(self, current_pid, action):
        """ basically the same as day phase voting """
        content = parse_xml_content(action, TAG_MAFIA_VOTE, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_MAFIA_VOTE}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid mafia vote action: {action}")
            return
            
        # extract and validate vote
        match = self.voting_pattern.search(content)
        if not match:
            self.state.set_invalid_move(player_id=current_pid, reason=f"The vote was not submitted in the correct format.")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid mafia vote format: {action}")
            return
        
        voted_pid = int(match.group(1))
        if self.state.game_state is not None and "votes" in self.state.game_state:
            self.state.game_state["votes"][current_pid] = voted_pid
        
        # count vote and broadcast to all mafia players
        if self.state.game_state is not None and "player_roles" in self.state.game_state and "alive_players" in self.state.game_state:
            mafia_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Mafia" and pid in self.state.game_state["alive_players"]]
            for pid in mafia_pids:
                self.state.add_observation(from_id=current_pid, to_id=pid, message=content)

        # check if everybody has voted
        if not self.next_player_ids:
            # evaluate votes and update observations accordingly
            if self.state.game_state is not None and "votes" in self.state.game_state:
                self.state.game_state["to_be_eliminated"] = self._evaluate_votes()
                # if no majority vote, use the most suggested target from discussion
                if self.state.game_state["to_be_eliminated"] is None and "kill_suggestions" in self.state.game_state:
                    max_suggestions = max(self.state.game_state["kill_suggestions"].values())
                    top_candidates = [pid for pid, count in self.state.game_state["kill_suggestions"].items() if count == max_suggestions]
                    # Only kill if there's exactly one most suggested target
                    if len(top_candidates) == 1:
                        self.state.game_state["to_be_eliminated"] = top_candidates[0]
                # clear suggestions for next night
                if "kill_suggestions" in self.state.game_state:
                    self.state.game_state["kill_suggestions"] = {}

    def _night_doctor(self, current_pid, action):
        """ check who the doctor whould like to save """
        content = parse_xml_content(action, TAG_PROTECT, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_PROTECT}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid protect action: {action}")
            return
            
        # extract and validate vote
        match = self.voting_pattern.search(content)
        if not match:
            self.state.set_invalid_move(player_id=current_pid, reason=f"The action was not submitted in the correct format.")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid protect format: {action}")
            return
        
        voted_pid = int(match.group(1))
        
        # check if voted_pid is to_be_eliminated
        self.state.add_observation(from_id=current_pid, to_id=current_pid, message=content)
        
        if self.state.game_state is not None and "to_be_eliminated" in self.state.game_state and self.state.game_state["to_be_eliminated"] is not None and voted_pid == self.state.game_state["to_be_eliminated"]:
            # save
            self.state.game_state["to_be_eliminated"] = None


    def _night_detective(self, current_pid, action):
        """ can check status of a single player """
        content = parse_xml_content(action, TAG_INVESTIGATE, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_INVESTIGATE}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid investigate action: {action}")
            return
            
        match = self.voting_pattern.search(content)
        if not match:
            self.state.set_invalid_move(player_id=current_pid, reason=f"The action was not submitted in the correct format.")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid investigate format: {action}")
            return
        
        voted_pid = int(match.group(1))
        if self.state.game_state is not None and "player_roles" in self.state.game_state:
            mafia_set = [pid for pid, role in self.state.game_state["player_roles"].items() if role == "Mafia"]
            if voted_pid in mafia_set:
                observation = f"Player {voted_pid} is part of the Mafia"
            else:
                observation = f"Player {voted_pid} is NOT part of the Mafia"

            self.state.add_observation(from_id=ta.GAME_ID, to_id=current_pid, message=observation)
            if "detective_inspected" in self.state.game_state:
                self.state.game_state["detective_inspected"].append(voted_pid)
            if "player_roles" in self.state.game_state:
                not_detective_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role != "Detective"]
                not_detective_observation = "The detective has seen an undisclosed player's role"
                for pid in not_detective_pids:
                    self.state.add_observation(from_id=ta.GAME_ID, to_id=pid, message=not_detective_observation)

    def _night_mafia_discussion(self, current_pid, action):
        """ Handle mafia discussion phase - only allow pointing to targets """
        content = parse_xml_content(action, TAG_MAFIA_SUGGEST, include_tags=True)
        if content is None:
            self.state.set_invalid_move(player_id=current_pid, reason=f"Response must be wrapped in <{TAG_MAFIA_SUGGEST}> tags")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid mafia suggest action: {action}")
            return
            
        # extract and validate target
        match = self.voting_pattern.search(content)
        if not match:
            self.state.set_invalid_move(player_id=current_pid, reason=f"The suggestion was not submitted in the correct format.")
            self.state.add_observation(from_id=current_pid, to_id=DEBUG_ID, message=f"[DEBUG] Invalid mafia suggest format: {action}")
            return
        
        target_pid = int(match.group(1))
        # broadcast to all mafia players
        if self.state.game_state is not None and "player_roles" in self.state.game_state and "alive_players" in self.state.game_state:
            mafia_pids = [pid for pid, role in self.state.game_state["player_roles"].items() if role=="Mafia" and pid in self.state.game_state["alive_players"]]
            for pid in mafia_pids:
                self.state.add_observation(from_id=current_pid, to_id=pid, message=content)

            # track suggestions for default target
            if "kill_suggestions" not in self.state.game_state:
                self.state.game_state["kill_suggestions"] = {}
            if "kill_suggestions" in self.state.game_state:
                self.state.game_state["kill_suggestions"][target_pid] = self.state.game_state["kill_suggestions"].get(target_pid, 0) + 1


