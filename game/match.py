"""
game/match.py - Match state machine for Champion
==================================================
Tracks match phases, rounds, action declarations, and victory conditions.
"""
from dataclasses import dataclass, field
from typing import Optional
from game.enums import MatchPhase, Range, Advantage
from game.combat import FighterInstance


@dataclass
class MatchState:
    """Complete state of a match from lobby to conclusion."""
    team_a: list[FighterInstance]
    team_b: list[FighterInstance]
    phase: MatchPhase = MatchPhase.LOBBY
    round_number: int = 0
    rounds_won_a: int = 0
    rounds_won_b: int = 0
    current_volley: int = 0
    actions_declared_a: list = field(default_factory=list)
    actions_declared_b: list = field(default_factory=list)
    max_rounds: int = 3


def advance_phase(match: MatchState) -> MatchState:
    """Advance the match to the next phase."""
    phase_order = [
        MatchPhase.LOBBY,
        MatchPhase.FIGHTER_SELECT,
        MatchPhase.TECHNIQUE_SELECT,
        MatchPhase.ITEM_SELECT,
        MatchPhase.COMBAT,
        MatchPhase.ROUND_END,
        MatchPhase.MATCH_END,
    ]
    try:
        current_idx = phase_order.index(match.phase)
    except ValueError:
        return match
    next_idx = min(current_idx + 1, len(phase_order) - 1)
    match.phase = phase_order[next_idx]
    return match


def declare_actions(match: MatchState, team: str, actions: list) -> MatchState:
    """Store declared actions for a team."""
    if team == "a":
        match.actions_declared_a = actions
    elif team == "b":
        match.actions_declared_b = actions
    return match


def all_actions_declared(match: MatchState) -> bool:
    """Check if both teams have declared their actions."""
    return len(match.actions_declared_a) > 0 and len(match.actions_declared_b) > 0


def clear_actions(match: MatchState) -> MatchState:
    """Clear declared actions for the next volley."""
    match.actions_declared_a = []
    match.actions_declared_b = []
    match.current_volley += 1
    return match


def check_round_end(match: MatchState) -> Optional[str]:
    """Check if the round is over. Returns winning team ('a' or 'b') or None."""
    if match.phase != MatchPhase.COMBAT:
        return None

    a_alive = any(f.current_health > 0 for f in match.team_a)
    b_alive = any(f.current_health > 0 for f in match.team_b)

    if not a_alive and not b_alive:
        return "draw"
    if not b_alive:
        return "a"
    if not a_alive:
        return "b"
    return None


def apply_round_result(match: MatchState, winner: str) -> MatchState:
    """Record the result of a completed round."""
    match.round_number += 1
    if winner == "a":
        match.rounds_won_a += 1
    elif winner == "b":
        match.rounds_won_b += 1
    match.phase = MatchPhase.ROUND_END
    return match


def check_match_end(match: MatchState) -> Optional[str]:
    """Check if the match is over. Returns winner ('a' or 'b') or None."""
    wins_needed = (match.max_rounds // 2) + 1
    if match.rounds_won_a >= wins_needed:
        return "a"
    if match.rounds_won_b >= wins_needed:
        return "b"
    if match.round_number >= match.max_rounds:
        if match.rounds_won_a > match.rounds_won_b:
            return "a"
        if match.rounds_won_b > match.rounds_won_a:
            return "b"
        return "draw"
    return None


def reset_for_new_round(match: MatchState) -> MatchState:
    """Reset combatants for a new round."""
    for fighter in match.team_a + match.team_b:
        fighter.current_health = fighter.fighter_data.base_health
        fighter.current_range = Range.MEDIUM
        fighter.current_advantage = Advantage.NEUTRAL
        fighter.active_debuffs = []
        fighter.predictability = 0
        fighter.power_modifier = 0
        fighter.speed_modifier = 0
        fighter.damage_reduction = 0
    match.phase = MatchPhase.COMBAT
    match.current_volley = 0
    return match
