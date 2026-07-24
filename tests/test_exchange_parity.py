"""Local/online parity for per-exchange resolution.

These cover the shared combat helpers that both local play (``app.py``
``_run_combat_volley``) and the server (``server/combat_resolver.py``) call, so
the two code paths cannot drift:

* ``resolve_declared_technique`` — honor a declared technique only when the
  fighter selected it AND its base_action matches the declared action.
* ``apply_exchange_side_effects`` — apply an exchange's range/advantage/debuff
  side-effects to the fighters.
"""
from game.combat import (
    FighterInstance, ExchangeResult, resolve_exchange, resolve_declared_technique,
    apply_exchange_side_effects,
)
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect, load_all_techniques
from game.enums import ActionType, Range, Advantage, DebuffType


def _fighter(name="Test", speed=4):
    data = FighterData(
        id=name.lower(), name=name, description="", base_health=5, base_speed=speed,
        base_power=4, base_intellect=0, technique_ids=[], exclusive_technique_ids=[],
        panoply={},
    )
    return FighterInstance(fighter_data=data)


def _strike_tech(tech_id="power_strike"):
    return TechniqueData(id=tech_id, name="Power Strike", description="",
                         base_action=ActionType.STRIKE, effects=TechniqueEffect())


# --- resolve_declared_technique (Followup #3) --------------------------------

def test_declared_technique_none_when_no_technique_id():
    inst = _fighter()
    assert resolve_declared_technique(
        {"action": "strike", "technique_id": None}, inst, {}) is None


def test_declared_technique_none_when_not_selected():
    inst = _fighter()  # selected_techniques is empty
    tech = _strike_tech()
    assert resolve_declared_technique(
        {"action": "strike", "technique_id": "power_strike"}, inst,
        {"power_strike": tech}) is None


def test_declared_technique_none_when_action_does_not_match():
    inst = _fighter()
    inst.selected_techniques = ["power_strike"]
    tech = _strike_tech()  # base_action is STRIKE
    # Declared action is BLOCK — the strike technique must not be honored.
    assert resolve_declared_technique(
        {"action": "block", "technique_id": "power_strike"}, inst,
        {"power_strike": tech}) is None


def test_declared_technique_returned_when_selected_and_action_matches():
    inst = _fighter()
    inst.selected_techniques = ["power_strike"]
    tech = _strike_tech()
    assert resolve_declared_technique(
        {"action": "strike", "technique_id": "power_strike"}, inst,
        {"power_strike": tech}) is tech


# --- apply_exchange_side_effects (Followup #2) -------------------------------

def test_side_effects_apply_range_change_to_attacker():
    attacker, defender = _fighter("A"), _fighter("B")
    result = ExchangeResult(attacker_action=ActionType.AVOID,
                            defender_action=ActionType.AVOID, outcome="whiff",
                            range_change=Range.FAR)
    apply_exchange_side_effects(attacker, defender, result)
    assert attacker.current_range == Range.FAR


def test_side_effects_apply_attacker_advantage_change():
    attacker, defender = _fighter("A"), _fighter("B")
    result = ExchangeResult(attacker_action=ActionType.STRIKE,
                            defender_action=ActionType.FEINT, outcome="hit",
                            attacker_advantage_change=Advantage.OFFENSIVE)
    apply_exchange_side_effects(attacker, defender, result)
    assert attacker.current_advantage == Advantage.OFFENSIVE
    assert defender.current_advantage == Advantage.NEUTRAL


def test_side_effects_apply_defender_advantage_change():
    attacker, defender = _fighter("A"), _fighter("B")
    result = ExchangeResult(attacker_action=ActionType.FEINT,
                            defender_action=ActionType.COUNTER, outcome="hit",
                            defender_advantage_change=Advantage.DEFENSIVE)
    apply_exchange_side_effects(attacker, defender, result)
    assert defender.current_advantage == Advantage.DEFENSIVE
    assert attacker.current_advantage == Advantage.NEUTRAL


def test_side_effects_append_debuffs_to_defender_without_duplicates():
    attacker, defender = _fighter("A"), _fighter("B")
    result = ExchangeResult(attacker_action=ActionType.STRIKE,
                            defender_action=ActionType.FEINT, outcome="hit",
                            debuffs_applied=[DebuffType.WEAKENED])
    apply_exchange_side_effects(attacker, defender, result)
    assert defender.active_debuffs == [DebuffType.WEAKENED]
    # Re-applying the same debuff must not duplicate it.
    apply_exchange_side_effects(attacker, defender, result)
    assert defender.active_debuffs == [DebuffType.WEAKENED]


def test_side_effects_noop_when_result_carries_none():
    attacker, defender = _fighter("A"), _fighter("B")
    result = ExchangeResult(attacker_action=ActionType.STRIKE,
                            defender_action=ActionType.STRIKE, outcome="clash")
    apply_exchange_side_effects(attacker, defender, result)
    assert attacker.current_range == Range.MEDIUM
    assert attacker.current_advantage == Advantage.NEUTRAL
    assert defender.current_advantage == Advantage.NEUTRAL
    assert defender.active_debuffs == []


# --- Real-technique parity through the shared pipeline (Followups #2 + #3) ----
# These exercise the exact resolve-then-apply pipeline that local play
# (``app.py``) and the server (``server/combat_resolver.py``) now both run, with
# real technique data, so a debuff/advantage effect actually lands locally.

def test_real_debuff_technique_weakens_defender_locally():
    techniques = load_all_techniques("game/data/techniques")
    attacker, defender = _fighter("A", speed=5), _fighter("B", speed=3)
    attacker.selected_techniques = ["bone_crusher"]  # STRIKE, applies weakened
    tech = resolve_declared_technique(
        {"action": "strike", "technique_id": "bone_crusher"}, attacker, techniques)
    assert tech is not None
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT,
                              attacker_technique=tech, techniques=techniques)
    assert DebuffType.WEAKENED in result.debuffs_applied
    assert DebuffType.WEAKENED not in defender.active_debuffs  # not committed yet
    apply_exchange_side_effects(attacker, defender, result)
    assert DebuffType.WEAKENED in defender.active_debuffs


def test_real_advantage_technique_repositions_attacker_locally():
    techniques = load_all_techniques("game/data/techniques")
    attacker, defender = _fighter("A", speed=5), _fighter("B", speed=3)
    attacker.selected_techniques = ["defensive_stance"]  # BLOCK, gains defensive
    tech = resolve_declared_technique(
        {"action": "block", "technique_id": "defensive_stance"}, attacker, techniques)
    assert tech is not None
    result = resolve_exchange(attacker, defender, ActionType.BLOCK, ActionType.STRIKE,
                              attacker_technique=tech, techniques=techniques)
    assert result.attacker_advantage_change == Advantage.DEFENSIVE
    assert attacker.current_advantage == Advantage.NEUTRAL  # not committed yet
    apply_exchange_side_effects(attacker, defender, result)
    assert attacker.current_advantage == Advantage.DEFENSIVE


def test_real_technique_ignored_when_declared_action_mismatches():
    """The action-matched guard rejects a real technique used under the wrong action."""
    techniques = load_all_techniques("game/data/techniques")
    attacker = _fighter("A")
    attacker.selected_techniques = ["bone_crusher"]  # a STRIKE technique
    assert resolve_declared_technique(
        {"action": "block", "technique_id": "bone_crusher"}, attacker, techniques) is None
