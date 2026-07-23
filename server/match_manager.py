"""
server/match_manager.py - Match lifecycle management
======================================================
Handles lobby queue, player pairing, and match state.
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from server.game_data import GameData


@dataclass
class ServerMatch:
    """Server-side match tracking."""
    match_id: str
    mode: str
    match_state: any  # MatchState
    player_a_id: str = ""
    player_b_id: str = ""
    player_a_name: str = ""
    player_b_name: str = ""
    phase: str = "lobby"
    fighter_choices: dict = field(default_factory=dict)
    technique_choices: dict = field(default_factory=dict)
    item_choices: dict = field(default_factory=dict)
    ready_for_round: set = field(default_factory=set)


class MatchManager:
    """Manages matchmaking and active matches."""

    def __init__(self, data: GameData = None):
        self.data = data if data is not None else GameData.load()
        self._queue: list[tuple[str, str]] = []  # (player_id, mode)
        self._matches: dict[str, ServerMatch] = {}

    def add_to_queue(self, player_id: str, mode: str) -> Optional[str]:
        """Add player to queue. Returns match_id if paired, None otherwise.

        NOTE: When a match_id is returned, the caller (e.g. server/main.py)
        MUST set session.current_match_id on both players' sessions so that
        subsequent messages (select_fighter, declare_actions, etc.) can
        look up the match via the session.
        """
        # Check for existing match
        for pid, qmode in self._queue:
            if qmode == mode and pid != player_id:
                self._queue.remove((pid, qmode))
                match_id = str(uuid.uuid4())[:8]
                match = ServerMatch(match_id=match_id, mode=mode, match_state=None)
                match.player_a_id = pid
                match.player_b_id = player_id
                self._matches[match_id] = match
                return match_id
        self._queue.append((player_id, mode))
        return None

    def set_fighter_choice(self, match_id: str, player_id: str, fighter_id: str) -> None:
        match = self._matches.get(match_id)
        if match:
            match.fighter_choices[player_id] = fighter_id

    def set_technique_choices(self, match_id: str, player_id: str, technique_ids: list[str]) -> None:
        match = self._matches.get(match_id)
        if match:
            match.technique_choices[player_id] = technique_ids

    def set_item_choices(self, match_id: str, player_id: str, item_ids: list[str]) -> None:
        match = self._matches.get(match_id)
        if match:
            match.item_choices[player_id] = item_ids
            if match.match_state is None and self._all_choices_in(match):
                self._build_match_state(match)

    def _all_choices_in(self, match: ServerMatch) -> bool:
        players = {match.player_a_id, match.player_b_id}
        return (players <= set(match.fighter_choices)
                and players <= set(match.technique_choices)
                and players <= set(match.item_choices))

    def _build_match_state(self, match: ServerMatch) -> None:
        """Build both fighter instances (buffs + reactions) and start combat."""
        from game.combat import FighterInstance, apply_buffs
        from game.match import MatchState, advance_phase
        from game.reactions import attach_reactions

        instances = {}
        for player_id, team in ((match.player_a_id, "a"), (match.player_b_id, "b")):
            fighter = self.data.fighters[match.fighter_choices[player_id]]
            inst = FighterInstance(
                fighter_data=fighter,
                selected_techniques=list(match.technique_choices.get(player_id, [])),
                selected_items=list(match.item_choices.get(player_id, [])),
            )
            inst = apply_buffs(inst, self.data.items)
            attach_reactions(inst, self.data.feats, self.data.items)
            instances[team] = inst
        match.match_state = MatchState(team_a=[instances["a"]], team_b=[instances["b"]])
        for _ in range(4):  # LOBBY -> FIGHTER_SELECT -> TECHNIQUE_SELECT -> ITEM_SELECT -> COMBAT
            advance_phase(match.match_state)

    def get_match(self, match_id: str) -> Optional[ServerMatch]:
        return self._matches.get(match_id)

    def get_player_team(self, match: ServerMatch, player_id: str) -> str:
        if match.player_a_id == player_id:
            return "a"
        return "b"

    def resolve_volley(self, match_id: str, player_id: str, actions: list) -> dict:
        match = self._matches.get(match_id)
        if not match:
            return {"type": "error", "message": "Match not found"}

        team = self.get_player_team(match, player_id)
        if team == "a":
            match.match_state.actions_declared_a = actions
        else:
            match.match_state.actions_declared_b = actions

        from game.match import all_actions_declared
        if not all_actions_declared(match.match_state):
            return {"type": "actions_received", "team": team}

        from server.combat_resolver import resolve_volley_server
        result = resolve_volley_server(match, self.data.techniques)

        from game.match import clear_actions, check_round_end, apply_round_result
        clear_actions(match.match_state)

        round_winner = check_round_end(match.match_state, max_volleys=17)
        if round_winner:
            # Check if this was a turn-limit win (both fighters still alive)
            a_alive = any(f.current_health > 0 for f in match.match_state.team_a)
            b_alive = any(f.current_health > 0 for f in match.match_state.team_b)
            if a_alive and b_alive and round_winner != "draw":
                result["time_up"] = True
            apply_round_result(match.match_state, round_winner)
            from game.match import check_match_end
            match_winner = check_match_end(match.match_state)
            result["round_end"] = True
            result["round_winner"] = round_winner
            if match_winner:
                result["match_end"] = True
                result["match_winner"] = match_winner

        return result

    def player_ready_for_round(self, match_id: str, player_id: str) -> None:
        match = self._matches.get(match_id)
        if not match or match.match_state is None:
            return
        match.ready_for_round.add(player_id)
        if len(match.ready_for_round) >= 2:
            from game.match import reset_for_new_round
            from game.combat import apply_buffs
            reset_for_new_round(match.match_state)
            for inst in match.match_state.team_a + match.match_state.team_b:
                apply_buffs(inst, self.data.items)
            match.ready_for_round = set()
