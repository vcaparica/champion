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
        base_health=5, base_speed=4, base_power=5,
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


def test_check_round_end_turn_limit_less_damage_wins():
    """At turn limit, fighter who took less damage should win."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 17
    # Both alive, but A took less damage
    match.team_a[0].damage_taken_this_round = 10
    match.team_b[0].damage_taken_this_round = 25
    assert check_round_end(match, max_volleys=17) == "a"


def test_check_round_end_turn_limit_team_b_wins():
    """At turn limit, team B wins if fighter B took less damage."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 17
    match.team_a[0].damage_taken_this_round = 30
    match.team_b[0].damage_taken_this_round = 5
    assert check_round_end(match, max_volleys=17) == "b"


def test_check_round_end_turn_limit_equal_damage_draw():
    """At turn limit, equal damage taken should be a draw."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 17
    match.team_a[0].damage_taken_this_round = 20
    match.team_b[0].damage_taken_this_round = 20
    assert check_round_end(match, max_volleys=17) == "draw"


def test_check_round_end_turn_limit_not_reached():
    """Before turn limit, health-based check should still work normally."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 10
    match.team_a[0].damage_taken_this_round = 5
    match.team_b[0].damage_taken_this_round = 50
    # Turn limit not reached, both alive, so no winner
    assert check_round_end(match, max_volleys=17) is None


def test_check_round_end_health_zero_still_wins():
    """Health reaching zero should still win even before turn limit."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 5
    match.team_b[0].current_health = 0
    # Health-based win takes priority
    assert check_round_end(match, max_volleys=17) == "a"


def test_reset_clears_reaction_state():
    from game.match import MatchState, reset_for_new_round
    from game.combat import FighterInstance
    from game.fighter import FighterData
    fd = FighterData("t", "T", "d", 5, 4, 5, [], [], {})
    a = FighterInstance(fighter_data=fd)
    b = FighterInstance(fighter_data=fd)
    a.reaction_state["burn_stacks"] = 3
    a.reaction_state["once_round"] = {0}
    match = MatchState(team_a=[a], team_b=[b])
    reset_for_new_round(match)
    assert a.reaction_state == {}
