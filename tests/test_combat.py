"""Tests for combat engine interaction matrix and resolution."""
import pytest
from game.combat import (
    FighterInstance, ExchangeResult, resolve_exchange, apply_buffs,
    compute_damage, get_effective_speed, get_effective_intellect,
    compare_speed_order
)
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.item import ItemData, ItemBuff
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
            slot=BodySlot.RING,
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
    # effective speed check: 2 items -> -1 penalty, base 4 -> 3
    assert get_effective_speed(instance) == 3


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


def test_intellect_damage_scale_adds_damage():
    """intellect_damage_scale should add (intellect * scale) to damage."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    defender = make_test_fighter("Defender", health=5)
    tech = TechniqueData(
        id="mind_over_matter", name="Mind Over Matter", description="",
        base_action=ActionType.STRIKE,
        effects=TechniqueEffect(intellect_damage_scale=1),
        predictability_increase=2
    )
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    base = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    # Mind Over Matter adds intellect (6) to damage
    assert result.damage_to_defender == base.damage_to_defender + 6


def test_opponent_intellect_scale_damage():
    """opponent_intellect_scale should deal more damage vs low-intellect opponents."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    dumb_defender = make_test_fighter("Dumb", health=5, intellect=2)
    smart_defender = make_test_fighter("Smart", health=5, intellect=6)
    tech = TechniqueData(
        id="exploit_weakness", name="Exploit Weakness", description="",
        base_action=ActionType.FEINT,
        effects=TechniqueEffect(opponent_intellect_scale=1),
        predictability_increase=2
    )
    result_dumb = resolve_exchange(attacker, dumb_defender, ActionType.FEINT, ActionType.BLOCK, attacker_technique=tech)
    result_smart = resolve_exchange(attacker, smart_defender, ActionType.FEINT, ActionType.BLOCK, attacker_technique=tech)
    # Exploit Weakness: +(7 - opponent_intellect) damage. vs dumb(2): +5, vs smart(6): +1
    assert result_dumb.damage_to_defender > result_smart.damage_to_defender


def test_intellect_damage_reduction():
    """intellect_damage_reduction should add (intellect * scale / 2 rounded up) to DR."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    defender = make_test_fighter("Defender", health=5)
    tech_no_dr = TechniqueData(
        id="basic_block", name="Basic Block", description="",
        base_action=ActionType.BLOCK,
        effects=TechniqueEffect(),
        predictability_increase=1
    )
    tech_dr = TechniqueData(
        id="iron_discipline", name="Iron Discipline", description="",
        base_action=ActionType.BLOCK,
        effects=TechniqueEffect(intellect_damage_reduction=1),
        predictability_increase=1
    )
    result_no = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.BLOCK, defender_technique=tech_no_dr)
    result_dr = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.BLOCK, defender_technique=tech_dr)
    # Blocked strike deals 0 damage either way, so test with FEINT which bypasses block
    result_no2 = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK, defender_technique=tech_no_dr)
    result_dr2 = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK, defender_technique=tech_dr)
    # When defender uses block vs feint, the outcome is "bypassed" with damage to defender
    # Defender_technique DR reduction should reduce the incoming damage
    assert result_dr2.outcome == "bypassed"
    assert result_dr2.damage_to_defender < result_no2.damage_to_defender


def test_require_intellect_advantage_blocks_effect():
    """require_intellect_advantage should only allow effect when own intellect >= opponent."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    smarter_defender = make_test_fighter("SmartDef", health=5, intellect=7)
    dumber_defender = make_test_fighter("DumbDef", health=5, intellect=3)
    tech = TechniqueData(
        id="read_pattern", name="Read the Pattern", description="",
        base_action=ActionType.COUNTER,
        effects=TechniqueEffect(damage_modifier=3, require_intellect_advantage=True),
        predictability_increase=2
    )
    # Vs dumber defender: intellect advantage holds, +3 damage applies
    result_dumb = resolve_exchange(attacker, dumber_defender, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=tech)
    # Vs smarter defender: intellect disadvantage, damage modifier should be nullified
    result_smart = resolve_exchange(attacker, smarter_defender, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=tech)
    # The counter succeeds in both, but damage should differ
    assert result_dumb.outcome == "countered"
    assert result_smart.outcome == "countered"
    assert result_dumb.damage_to_defender > result_smart.damage_to_defender


def test_apply_buffs_with_scales_with():
    """Item buffs with scales_with should multiply value by fighter's attribute."""
    fighter = make_test_fighter("Test", health=5, power=5, intellect=6)
    items = {
        "smart_ring": ItemData(
            id="smart_ring", name="Smart Ring", description="",
            slot=BodySlot.RING,
            passive_buffs=[ItemBuff(BuffType.POWER, 1, scales_with="intellect")]
        )
    }
    fighter.selected_items = ["smart_ring"]
    fighter = apply_buffs(fighter, items)
    # Intellect 6, base value 1: power_modifier = 1 * 6 = 6
    assert fighter.power_modifier == 6


def test_intellect_to_speed():
    """intellect_to_speed should set speed equal to intellect for the exchange."""
    # Fighter has speed 1 but intellect 6, so combat_speed should be 6 with this technique
    attacker = make_test_fighter("Attacker", power=5, speed=1, intellect=6)
    defender = make_test_fighter("Defender", health=5, speed=4)
    tech = TechniqueData(
        id="mental_alacrity", name="Mental Alacrity", description="",
        base_action=ActionType.AVOID,
        effects=TechniqueEffect(intellect_to_speed=True),
        predictability_increase=1
    )
    # The technique makes speed = intellect for the exchange
    result = resolve_exchange(attacker, defender, ActionType.AVOID, ActionType.AVOID, attacker_technique=tech, defender_technique=None)
    # Both avoid -> both whiff with range change to far
    assert result.outcome == "whiff"
    assert result.range_change == Range.FAR


def test_fighter_instance_reaction_fields_default():
    from game.combat import FighterInstance
    from game.fighter import FighterData
    fd = FighterData("t", "T", "d", 5, 4, 5, [], [], {})
    inst = FighterInstance(fighter_data=fd)
    assert inst.feat is None
    assert inst.reactions == []
    assert inst.reaction_state == {}
    # Independent instances must not share the mutable defaults
    other = FighterInstance(fighter_data=fd)
    inst.reactions.append("x")
    inst.reaction_state["k"] = 1
    assert other.reactions == []
    assert other.reaction_state == {}


def test_assess_action_type_exists():
    """ASSESS is the 7th combat action."""
    from game.enums import ActionType
    assert ActionType.ASSESS.value == "assess"
    assert len(list(ActionType)) == 7


@pytest.mark.parametrize("a_act,d_act,expected", [
    (ActionType.ASSESS, ActionType.STRIKE, "assessed"),
    (ActionType.ASSESS, ActionType.CHARGE, "assessed"),
    (ActionType.ASSESS, ActionType.FEINT, "assessed"),
    (ActionType.ASSESS, ActionType.BLOCK, "assessed"),
    (ActionType.ASSESS, ActionType.AVOID, "assessed"),
    (ActionType.ASSESS, ActionType.COUNTER, "assessed"),
    (ActionType.ASSESS, ActionType.ASSESS, "assessed"),
    (ActionType.BLOCK, ActionType.ASSESS, "assessed"),
    (ActionType.AVOID, ActionType.ASSESS, "assessed"),
    (ActionType.COUNTER, ActionType.ASSESS, "assessed"),
    (ActionType.STRIKE, ActionType.ASSESS, "hit"),
    (ActionType.CHARGE, ActionType.ASSESS, "hit"),
    (ActionType.FEINT, ActionType.ASSESS, "hit"),
])
def test_assess_matrix_outcomes(a_act, d_act, expected):
    attacker = make_test_fighter("Attacker", power=5, speed=6)
    defender = make_test_fighter("Defender", power=5, speed=3)
    result = resolve_exchange(attacker, defender, a_act, d_act)
    assert result.outcome == expected


def test_assess_failing_cells_deal_damage():
    """Strike/Charge vs Assess deal damage to the assessing defender."""
    for atk in (ActionType.STRIKE, ActionType.CHARGE):
        attacker = make_test_fighter("A", power=5, speed=6)
        defender = make_test_fighter("D", speed=3)
        result = resolve_exchange(attacker, defender, atk, ActionType.ASSESS)
        assert result.damage_to_defender > 0
        assert result.damage_to_attacker == 0


def test_assess_succeeding_cells_deal_no_damage():
    """Succeeding Assess cells deal no damage to either side."""
    attacker = make_test_fighter("A", power=5, speed=6)
    defender = make_test_fighter("D", power=5, speed=3)
    result = resolve_exchange(attacker, defender, ActionType.ASSESS, ActionType.STRIKE)
    assert result.damage_to_defender == 0
    assert result.damage_to_attacker == 0


def test_feint_vs_assess_doubles_damage():
    """Feint vs Assess deals double the feint's resolved damage."""
    base = resolve_exchange(
        make_test_fighter("A", power=5), make_test_fighter("D"),
        ActionType.FEINT, ActionType.BLOCK,
    )
    doubled = resolve_exchange(
        make_test_fighter("A", power=5), make_test_fighter("D"),
        ActionType.FEINT, ActionType.ASSESS,
    )
    assert doubled.damage_to_defender == base.damage_to_defender * 2


def test_executioners_gambit_pays_off_on_the_defender_side():
    """Talon's exclusive counter is used almost always from the defender side
    (Talon is the slowest fighter). Its Health-scaled damage must actually land
    there -- this is the whole point of choosing a defender-honored effect.

    Slow defender: health 4, speed 2. A fast striker walks into the counter.
    The (STRIKE, COUNTER) cell deals the defender's damage to the attacker.
    Loaded counter must beat a plain counter by damage_modifier (2) plus
    health_damage_scale * effective Health (1 * 4) = +6.
    """
    defender = make_test_fighter("Talon", health=4, speed=2, power=6)
    attacker = make_test_fighter("Foe", health=5, speed=6, power=3)
    gambit = TechniqueData(
        id="executioners_gambit", name="Executioner's Gambit", description="d",
        base_action=ActionType.COUNTER,
        effects=TechniqueEffect(damage_modifier=2, health_damage_scale=1))
    plain = TechniqueData(
        id="plain_counter", name="Plain", description="d",
        base_action=ActionType.COUNTER, effects=TechniqueEffect())

    base = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.COUNTER,
                            defender_technique=plain)
    loaded = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.COUNTER,
                              defender_technique=gambit)
    assert base.outcome == "countered"
    assert loaded.damage_to_attacker == base.damage_to_attacker + 6
