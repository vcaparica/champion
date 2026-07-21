"""Tests for match state machine."""
from game.match import (
    MatchState, advance_phase, declare_actions,
    all_actions_declared, check_round_end, check_match_end
)
from game.combat import FighterInstance
from game.fighter import FighterData
from game.enums import MatchPhase


def make_test_fighter(name="Test"):
    data = FighterData(
        id=name.lower(), name=name, description="",
        base_health=100, base_speed=5, base_power=8,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    return FighterInstance(fighter_data=data)


def make_test_action():
    return {"action": "strike", "technique_id": None, "target_id": "opponent"}


def test_match_initial_phase():
    """New match should start in LOBBY phase."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    assert match.phase == MatchPhase.LOBBY
    assert match.round_number == 0
    assert match.rounds_won_a == 0
    assert match.rounds_won_b == 0


def test_advance_to_fighter_select():
    """Advancing from LOBBY should go to FIGHTER_SELECT."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match = advance_phase(match)
    assert match.phase == MatchPhase.FIGHTER_SELECT


def test_phase_progression():
    """Phases should progress in correct order."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    phases = []
    for _ in range(7):
        match = advance_phase(match)
        phases.append(match.phase)

    assert phases == [
        MatchPhase.FIGHTER_SELECT,
        MatchPhase.TECHNIQUE_SELECT,
        MatchPhase.ITEM_SELECT,
        MatchPhase.COMBAT,
        MatchPhase.ROUND_END,
        MatchPhase.MATCH_END,
        MatchPhase.MATCH_END,
    ]


def test_declare_actions():
    """declare_actions should store actions for the correct team."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    actions = [make_test_action(), make_test_action(), make_test_action()]
    match = declare_actions(match, "a", actions)
    assert match.actions_declared_a == actions
    assert match.actions_declared_b == []


def test_all_actions_declared():
    """all_actions_declared should return True only when both teams have declared."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    assert all_actions_declared(match) is False

    match = declare_actions(match, "a", [make_test_action()] * 3)
    assert all_actions_declared(match) is False

    match = declare_actions(match, "b", [make_test_action()] * 3)
    assert all_actions_declared(match) is True


def test_check_round_end():
    """check_round_end should return None when fighters still have health."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    assert check_round_end(match) is None


def test_check_round_end_fighter_dead():
    """check_round_end should return winning team when a fighter is at 0 health."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.team_b[0].current_health = 0
    assert check_round_end(match) == "a"


def test_check_match_end():
    """check_match_end should return winner after 2 round wins."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.round_number = 1
    match.rounds_won_a = 2
    match.rounds_won_b = 0
    match.phase = MatchPhase.ROUND_END
    assert check_match_end(match) == "a"


def test_check_match_end_not_over():
    """check_match_end should return None when no one has won 2 rounds."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.round_number = 1
    match.rounds_won_a = 1
    match.rounds_won_b = 0
    match.phase = MatchPhase.ROUND_END
    assert check_match_end(match) is None
