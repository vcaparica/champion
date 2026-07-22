"""Tests for Speed-based technique and item effects in resolve_exchange."""
from game.combat import FighterInstance, resolve_exchange
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.enums import ActionType


def mk(speed, power=5, intellect=4, health=7):
    data = FighterData(id="t", name="T", description="", base_health=health,
                       base_speed=speed, base_power=power, base_intellect=intellect,
                       technique_ids=[], exclusive_technique_ids=[], panoply={})
    return FighterInstance(fighter_data=data)


def tech(action, **effects):
    return TechniqueData(id="x", name="X", description="", base_action=action,
                         effects=TechniqueEffect(**effects), predictability_increase=1)


def test_speed_instead_of_power_uses_speed():
    atk = mk(speed=7, power=3)
    dfn = mk(speed=2, power=5)
    t = tech(ActionType.STRIKE, speed_instead_of_power=True)
    res = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT, attacker_technique=t)
    assert res.damage_to_defender == 7  # speed 7, neutral advantage, no DR


def test_speed_damage_scale_charge():
    atk = mk(speed=6, power=4)
    dfn = mk(speed=3, power=5)
    t = tech(ActionType.CHARGE, speed_damage_scale=1)
    res = resolve_exchange(atk, dfn, ActionType.CHARGE, ActionType.BLOCK, attacker_technique=t)
    assert res.damage_to_defender == 10  # power 4 + speed 6


def test_speed_diff_scale_feint():
    atk = mk(speed=7, power=4)
    dfn = mk(speed=2, power=5)
    t = tech(ActionType.FEINT, speed_diff_scale=1)
    res = resolve_exchange(atk, dfn, ActionType.FEINT, ActionType.BLOCK, attacker_technique=t)
    assert res.damage_to_defender == 9  # power 4 + (7-2)


def test_speed_diff_scale_min_zero_when_slower():
    atk = mk(speed=2, power=4)
    dfn = mk(speed=7, power=5)
    t = tech(ActionType.FEINT, speed_diff_scale=1)
    res = resolve_exchange(atk, dfn, ActionType.FEINT, ActionType.BLOCK, attacker_technique=t)
    assert res.damage_to_defender == 4  # no bonus when slower


def test_speed_damage_reduction_defender():
    atk = mk(speed=3, power=6)   # feinting
    dfn = mk(speed=7, power=4)   # blocking with Quickened Guard
    guard = tech(ActionType.BLOCK, speed_damage_reduction=1)
    res = resolve_exchange(atk, dfn, ActionType.FEINT, ActionType.BLOCK, defender_technique=guard)
    # FEINT vs BLOCK -> bypassed, damage_to_defender = a_damage 6 - ceil(7/2)=4 -> 2
    assert res.outcome == "bypassed"
    assert res.damage_to_defender == 2


def test_require_speed_advantage_pass():
    atk = mk(speed=6, power=4)
    dfn = mk(speed=3, power=5)
    t = tech(ActionType.COUNTER, damage_modifier=3, require_speed_advantage=True)
    res = resolve_exchange(atk, dfn, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=t)
    assert res.damage_to_defender == 7  # power 4 + 3


def test_require_speed_advantage_fail():
    atk = mk(speed=2, power=4)
    dfn = mk(speed=6, power=5)
    t = tech(ActionType.COUNTER, damage_modifier=3, require_speed_advantage=True)
    res = resolve_exchange(atk, dfn, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=t)
    assert res.damage_to_defender == 4  # +3 suppressed


def test_speed_diff_item_offense_bonus():
    atk = mk(speed=7, power=4)
    atk.speed_diff_damage_bonus = 1
    dfn = mk(speed=2, power=5)
    res = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT)
    assert res.damage_to_defender == 9  # power 4 + (7-2)


def test_speed_diff_item_defense_reduction():
    atk = mk(speed=2, power=6)
    dfn = mk(speed=7, power=4)
    dfn.speed_diff_damage_reduction = 1
    res = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT)
    # damage_to_defender = a_damage 6 - (7-2)=5 -> floor 1
    assert res.damage_to_defender == 1
