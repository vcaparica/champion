"""Tests for technique data model and loader."""
import json
import os
import tempfile
import pytest
from game.technique import TechniqueData, TechniqueEffect, load_technique, load_all_techniques
from game.enums import ActionType


TECHNIQUE_JSON = {
    "id": "iron_wall",
    "name": "Iron Wall",
    "description": "An unbreakable defensive stance that damages attackers.",
    "base_action": "block",
    "effects": {
        "damage_modifier": 3,
        "bypass_range": False,
        "heal_on_hit": 0,
        "reposition_to": None,
        "apply_debuff": None,
        "steal_item": False,
        "switch_own_item": False,
        "gain_advantage": "defensive",
        "multi_target": False
    },
    "predictability_increase": 2
}


def test_technique_effect_defaults():
    """TechniqueEffect should have sensible defaults."""
    effect = TechniqueEffect()
    assert effect.damage_modifier == 0
    assert effect.bypass_range is False
    assert effect.multi_target is False


def test_technique_data_from_effect():
    """TechniqueData should combine action and effects correctly."""
    effect = TechniqueEffect(damage_modifier=3, gain_advantage="defensive")
    tech = TechniqueData(
        id="iron_wall",
        name="Iron Wall",
        description="Unbreakable defense.",
        base_action=ActionType.BLOCK,
        effects=effect,
        predictability_increase=2
    )
    assert tech.base_action == ActionType.BLOCK
    assert tech.effects.damage_modifier == 3
    assert tech.effects.gain_advantage == "defensive"
    assert tech.predictability_increase == 2


def test_load_technique_from_json():
    """load_technique should parse a JSON file into TechniqueData."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(TECHNIQUE_JSON, f)
        temp_path = f.name

    try:
        tech = load_technique(temp_path)
        assert tech.id == "iron_wall"
        assert tech.base_action == ActionType.BLOCK
        assert tech.effects.damage_modifier == 3
        assert tech.effects.gain_advantage == "defensive"
    finally:
        os.unlink(temp_path)


def test_load_all_techniques():
    """load_all_techniques should load all technique JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "iron_wall.json"), "w") as f:
            json.dump(TECHNIQUE_JSON, f)
        t2 = dict(TECHNIQUE_JSON, id="shield_bash", name="Shield Bash", base_action="strike")
        with open(os.path.join(tmpdir, "shield_bash.json"), "w") as f:
            json.dump(t2, f)

        techniques = load_all_techniques(tmpdir)
        assert len(techniques) == 2
        assert "iron_wall" in techniques
        assert techniques["shield_bash"].base_action == ActionType.STRIKE


def test_technique_effect_intellect_fields_default():
    """New intellect fields should default to 0/False."""
    effect = TechniqueEffect()
    assert effect.intellect_damage_scale == 0
    assert effect.opponent_intellect_scale == 0
    assert effect.intellect_to_speed is False
    assert effect.intellect_damage_reduction == 0
    assert effect.require_intellect_advantage is False


def test_load_technique_with_intellect_effects():
    """load_technique should parse intellect effect fields from JSON."""
    data = dict(TECHNIQUE_JSON)
    data["effects"]["intellect_damage_scale"] = 1
    data["effects"]["intellect_to_speed"] = True
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    try:
        tech = load_technique(temp_path)
        assert tech.effects.intellect_damage_scale == 1
        assert tech.effects.intellect_to_speed is True
    finally:
        os.unlink(temp_path)


def test_assess_technique_effect_fields_load(tmp_path):
    import json
    from game.technique import load_technique
    data = {
        "id": "read_the_blade", "name": "Read the Blade",
        "description": "Found weak spot.", "base_action": "assess",
        "predictability_increase": 1,
        "effects": {
            "assess_next_counter_bonus": 3,
            "assess_next_damage_half": True,
            "assess_speed_buff": 2, "assess_speed_buff_volleys": 3,
            "assess_reveal_unused_technique": True,
            "assess_reveal_item": False,
        },
    }
    p = tmp_path / "read_the_blade.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    tech = load_technique(str(p))
    eff = tech.effects
    assert eff.assess_next_counter_bonus == 3
    assert eff.assess_next_damage_half is True
    assert eff.assess_speed_buff == 2
    assert eff.assess_speed_buff_volleys == 3
    assert eff.assess_reveal_unused_technique is True
    assert eff.assess_reveal_item is False
