"""Tests for combat engine interaction matrix and resolution."""
import pytest
from game.combat import (
    FighterInstance, ExchangeResult, resolve_exchange, apply_buffs,
    compute_damage, get_effective_speed, get_effective_intellect,
    compare_speed_order
)
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.item import ItemData
from game.enums import ActionType, Range, Advantage, BodySlot, BuffType, DebuffType


def make_test_fighter(name="Test", health=5, speed=4, power=5, intellect=0):
    """Helper to create a minimal FighterInstance for testing.

    Note: health is the fighter-scale base_health (1-7).
    actual HP will be health * 10.
    """
    data = FighterData(
        id=name.lower(),
        name=name,
        description="A test fighter.",
        base_health=health,
        base_speed=speed,
        base_power=power,
        base_intellect=intellect,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={}
    )
    return FighterInstance(fighter_data=data)


def test_strike_hits_feint():
    """Strike should hit successfully against Feint."""
    attacker = make_test_fighter("Attacker", power=5)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0
    assert result.damage_to_attacker == 0


def test_strike_blocked_by_block():
    """Strike should be blocked by Block."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.BLOCK)
    assert result.outcome == "blocked"
    assert result.damage_to_defender == 0


def test_feint_bypasses_block():
    """Feint should bypass Block."""
    attacker = make_test_fighter("Attacker", power=5)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK)
    assert result.outcome == "bypassed"
    assert result.damage_to_defender > 0


def test_counter_beats_strike():
    """Counter should beat Strike."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender", power=5)
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.COUNTER)
    assert result.outcome == "countered"
    assert result.damage_to_attacker > 0


def test_charge_breaks_block():
    """Charge should break through Block."""
    attacker = make_test_fighter("Attacker", power=7)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.CHARGE, ActionType.BLOCK)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0


def test_avoid_dodges_strike():
    """Avoid should dodge Strike."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.AVOID)
    assert result.outcome == "miss"


def test_feint_catches_avoid():
    """Feint should catch Avoid."""
    attacker = make_test_fighter("Attacker", power=5)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.AVOID)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0


def test_strike_vs_strike_clash():
    """Strike vs Strike should be a clash."""
    attacker = make_test_fighter("Attacker", power=5)
    defender = make_test_fighter("Defender", power=5)
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.STRIKE)
    assert result.outcome == "clash"
    assert result.damage_to_defender > 0
    assert result.damage_to_attacker > 0


def test_counter_loses_to_block():
    """Counter should lose to Block."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.COUNTER, ActionType.BLOCK)
    assert result.outcome in ("blocked", "whiff")


def test_technique_damage_modifier():
    """Technique damage modifier should increase damage."""
    attacker = make_test_fighter("Attacker", power=5)
    defender = make_test_fighter("Defender")
    tech = TechniqueData(
        id="power_strike", name="Power Strike", description="",
        base_action=ActionType.STRIKE,
        effects=TechniqueEffect(damage_modifier=2),
        predictability_increase=1
    )
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    assert result.outcome == "hit"
    base_result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    assert result.damage_to_defender > base_result.damage_to_defender


def test_speed_determines_clash_damage():
    """Faster fighter should take less damage in a clash."""
    fast = make_test_fighter("Fast", speed=7, power=5)
    slow = make_test_fighter("Slow", speed=2, power=5)
    result = resolve_exchange(fast, slow, ActionType.STRIKE, ActionType.STRIKE)
    assert result.damage_to_attacker < result.damage_to_defender


def test_apply_buffs_modifies_stats():
    """apply_buffs should modify fighter instance stats from items."""
    instance = make_test_fighter("Test", health=5, power=5, speed=4)
    items = {
        "health_ring": ItemData(
            id="health_ring", name="Health Ring", description="",
            slot=BodySlot.RING1,
            passive_buffs=[{"buff_type": "health", "value": 8}]
        ),
        "power_gloves": ItemData(
            id="power_gloves", name="Power Gloves", description="",
            slot=BodySlot.HANDS,
            passive_buffs=[{"buff_type": "power", "value": 2}]
        )
    }
    # Need to convert dict buffs to ItemBuff objects
    from game.item import ItemBuff
    items["health_ring"].passive_buffs = [ItemBuff(BuffType.HEALTH, 8)]
    items["power_gloves"].passive_buffs = [ItemBuff(BuffType.POWER, 2)]

    instance.selected_items = ["health_ring", "power_gloves"]
    instance = apply_buffs(instance, items)
    assert instance.current_health == 58  # 5*10 + 8
    assert instance.fighter_data.base_power == 5
    # effective speed check
    assert get_effective_speed(instance) == 4


def test_heal_on_hit():
    """A technique with heal_on_hit should restore health on a successful hit."""
    attacker = make_test_fighter("Attacker", power=5, health=5)
    defender = make_test_fighter("Defender", health=5)
    initial_health = attacker.current_health

    tech = TechniqueData(
        id="life_strike", name="Life Strike", description="",
        base_action=ActionType.STRIKE,
        effects=TechniqueEffect(heal_on_hit=10),
        predictability_increase=1
    )

    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    assert result.outcome == "hit"
    assert attacker.current_health == initial_health + 10


def test_power_buff_increases_damage():
    """POWER buff from items should increase damage output."""
    attacker_buffed = make_test_fighter("Buffed", power=5, health=5)
    attacker_buffed.power_modifier = 2
    attacker_unbuffed = make_test_fighter("Unbuffed", power=5, health=5)
    defender_a = make_test_fighter("DefenderA", health=7)
    defender_b = make_test_fighter("DefenderB", health=7)

    result_buffed = resolve_exchange(attacker_buffed, defender_a, ActionType.STRIKE, ActionType.FEINT)
    result_unbuffed = resolve_exchange(attacker_unbuffed, defender_b, ActionType.STRIKE, ActionType.FEINT)

    assert result_buffed.outcome == "hit"
    assert result_unbuffed.outcome == "hit"
    assert result_buffed.damage_to_defender > result_unbuffed.damage_to_defender


def test_fighter_instance_defaults():
    """FighterInstance should initialize with defaults from FighterData."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    assert instance.current_health == 50  # base_health * 10
    assert instance.current_range == Range.MEDIUM
    assert instance.current_advantage == Advantage.NEUTRAL
    assert instance.selected_techniques == []
    assert instance.selected_items == []
    assert instance.active_debuffs == []
    assert instance.predictability == 0


def test_get_effective_intellect_basic():
    """get_effective_intellect should return base_intellect when no modifiers."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=6,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    assert get_effective_intellect(instance) == 6


def test_get_effective_intellect_with_modifier():
    """Intellect modifier from items should affect effective intellect."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=4,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    instance.intellect_modifier = 2
    assert get_effective_intellect(instance) == 6


def test_get_effective_intellect_dazed():
    """DAZED debuff should reduce effective intellect by 1."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=4,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    instance.active_debuffs = [DebuffType.DAZED]
    assert get_effective_intellect(instance) == 3  # 4 - 1


def test_get_effective_intellect_floor_one():
    """Effective intellect should never go below 1."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=1,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    instance.active_debuffs = [DebuffType.DAZED]
    assert get_effective_intellect(instance) == 1  # floor at 1


def test_compare_speed_order_faster_first():
    """Faster fighter should go first."""
    fast = make_test_fighter("Fast", speed=7, power=5)
    slow = make_test_fighter("Slow", speed=2, power=5)
    assert compare_speed_order(fast, slow) == -1  # f1 faster
    assert compare_speed_order(slow, fast) == 1   # f2 faster


def test_compare_speed_order_intellect_breaks_tie():
    """When speed is equal, higher intellect should go first."""
    smart = make_test_fighter("Smart", speed=4, power=5, health=5, intellect=6)
    dumb = make_test_fighter("Dumb", speed=4, power=5, health=5, intellect=3)
    assert compare_speed_order(smart, dumb) == -1  # f1 smarter
    assert compare_speed_order(dumb, smart) == 1   # f2 smarter


def test_compare_speed_order_true_tie():
    """When speed and intellect are equal, should be true tie."""
    f1 = make_test_fighter("A", speed=4, power=5, health=5, intellect=4)
    f2 = make_test_fighter("B", speed=4, power=5, health=5, intellect=4)
    assert compare_speed_order(f1, f2) == 0
