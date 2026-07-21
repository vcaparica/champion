"""Tests for combat engine interaction matrix and resolution."""
import pytest
from game.combat import (
    FighterInstance, ExchangeResult, resolve_exchange, apply_buffs,
    compute_damage, get_effective_speed
)
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.item import ItemData
from game.enums import ActionType, Range, Advantage, BodySlot, BuffType, DebuffType


def make_test_fighter(name="Test", health=100, speed=5, power=8):
    """Helper to create a minimal FighterInstance for testing."""
    data = FighterData(
        id=name.lower(),
        name=name,
        description="A test fighter.",
        base_health=health,
        base_speed=speed,
        base_power=power,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={}
    )
    return FighterInstance(fighter_data=data)


def test_strike_hits_feint():
    """Strike should hit successfully against Feint."""
    attacker = make_test_fighter("Attacker", power=8)
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
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK)
    assert result.outcome == "bypassed"
    assert result.damage_to_defender > 0


def test_counter_beats_strike():
    """Counter should beat Strike."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender", power=8)
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.COUNTER)
    assert result.outcome == "countered"
    assert result.damage_to_attacker > 0


def test_charge_breaks_block():
    """Charge should break through Block."""
    attacker = make_test_fighter("Attacker", power=10)
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
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.AVOID)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0


def test_strike_vs_strike_clash():
    """Strike vs Strike should be a clash."""
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender", power=8)
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
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    tech = TechniqueData(
        id="power_strike", name="Power Strike", description="",
        base_action=ActionType.STRIKE,
        effects=TechniqueEffect(damage_modifier=5),
        predictability_increase=1
    )
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    assert result.outcome == "hit"
    base_result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    assert result.damage_to_defender > base_result.damage_to_defender


def test_speed_determines_clash_damage():
    """Faster fighter should take less damage in a clash."""
    fast = make_test_fighter("Fast", speed=10, power=8)
    slow = make_test_fighter("Slow", speed=3, power=8)
    result = resolve_exchange(fast, slow, ActionType.STRIKE, ActionType.STRIKE)
    assert result.damage_to_attacker < result.damage_to_defender


def test_apply_buffs_modifies_stats():
    """apply_buffs should modify fighter instance stats from items."""
    instance = make_test_fighter("Test", health=100, power=8, speed=5)
    items = {
        "health_ring": ItemData(
            id="health_ring", name="Health Ring", description="",
            slot=BodySlot.RING1,
            passive_buffs=[{"buff_type": "health", "value": 20}]
        ),
        "power_gloves": ItemData(
            id="power_gloves", name="Power Gloves", description="",
            slot=BodySlot.HANDS,
            passive_buffs=[{"buff_type": "power", "value": 3}]
        )
    }
    # Need to convert dict buffs to ItemBuff objects
    from game.item import ItemBuff
    items["health_ring"].passive_buffs = [ItemBuff(BuffType.HEALTH, 20)]
    items["power_gloves"].passive_buffs = [ItemBuff(BuffType.POWER, 3)]

    instance.selected_items = ["health_ring", "power_gloves"]
    instance = apply_buffs(instance, items)
    assert instance.current_health == 120
    assert instance.fighter_data.base_power == 8
    # effective power check
    assert get_effective_speed(instance) == 5


def test_fighter_instance_defaults():
    """FighterInstance should initialize with defaults from FighterData."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=100, base_speed=5, base_power=8,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    assert instance.current_health == 100
    assert instance.current_range == Range.MEDIUM
    assert instance.current_advantage == Advantage.NEUTRAL
    assert instance.selected_techniques == []
    assert instance.selected_items == []
    assert instance.active_debuffs == []
    assert instance.predictability == 0
