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
