"""Tests that the data model accepts the new Speed fields."""
from game.enums import BuffType
from game.technique import _dict_to_technique
from game.item import _dict_to_item
from game.combat import FighterInstance
from game.fighter import FighterData


def test_new_buff_types_exist():
    assert BuffType("speed_diff_damage") == BuffType.SPEED_DIFF_DAMAGE
    assert BuffType("speed_diff_reduction") == BuffType.SPEED_DIFF_REDUCTION


def test_technique_effect_speed_fields_parse_and_default():
    t = _dict_to_technique({
        "id": "x", "name": "X", "description": "", "base_action": "strike",
        "effects": {"speed_instead_of_power": True, "speed_damage_scale": 2},
    })
    assert t.effects.speed_instead_of_power is True
    assert t.effects.speed_damage_scale == 2
    assert t.effects.speed_diff_scale == 0
    assert t.effects.speed_damage_reduction == 0
    assert t.effects.require_speed_advantage is False


def test_item_min_speed_parses_and_defaults():
    gated = _dict_to_item({
        "id": "x", "name": "X", "description": "", "slot": "feet",
        "passive_buffs": [{"buff_type": "power", "value": 2, "min_speed": 5}],
    })
    assert gated.passive_buffs[0].min_speed == 5
    plain = _dict_to_item({
        "id": "y", "name": "Y", "description": "", "slot": "feet",
        "passive_buffs": [{"buff_type": "power", "value": 2}],
    })
    assert plain.passive_buffs[0].min_speed is None


def test_fighter_instance_speed_diff_fields_default_zero():
    data = FighterData(id="t", name="T", description="", base_health=5,
                       base_speed=5, base_power=5, technique_ids=[],
                       exclusive_technique_ids=[], panoply={})
    inst = FighterInstance(fighter_data=data)
    assert inst.speed_diff_damage_bonus == 0
    assert inst.speed_diff_damage_reduction == 0


def test_technique_health_fields_parse_and_default():
    from game.technique import _dict_to_technique
    t = _dict_to_technique({
        "id": "x", "name": "X", "description": "", "base_action": "strike",
        "effects": {"health_damage_scale": 1},
    })
    assert t.effects.health_damage_scale == 1
    assert t.effects.health_damage_reduction == 0
