"""Tests for fighter data model and loader."""
import json
import os
import tempfile
import pytest
from game.fighter import FighterData, load_fighter, load_all_fighters
from game.enums import BodySlot


FIGHTER_JSON = {
    "id": "thorn",
    "name": "Thorn",
    "description": "A battle-hardened knight of the Iron Order.",
    "base_health": 5,
    "base_speed": 4,
    "base_power": 5,
    "technique_ids": ["iron_wall", "shield_bash", "pommel_strike", "war_cry",
                       "defensive_stance", "shield_wall", "last_stand", "rallying_call"],
    "exclusive_technique_ids": ["iron_wall", "last_stand"],
    "panoply": {
        "head": ["iron_helm", "crown_of_resolve"],
        "eyes": ["tactical_monocle"],
        "neck": ["guardian_amulet", "pendant_of_fortitude"],
        "clothing": ["reinforced_vest"],
        "armor": ["iron_plate", "field_armor"],
        "shoulders": ["pauldrons_of_the_bulwark", "mantle_of_endurance"],
        "arms": ["vambraces_of_deflection"],
        "hands": ["gauntlets_of_might", "grippers_of_steadiness"],
        "ring": ["ring_of_vitality", "band_of_iron_will"],
        "waist": ["girdle_of_stone"],
        "feet": ["greaves_of_the_ram", "sabatons_of_patience"]
    }
}


def test_fighter_data_from_dict():
    """FighterData should be constructable from a dict."""
    fighter = FighterData(
        id=FIGHTER_JSON["id"],
        name=FIGHTER_JSON["name"],
        description=FIGHTER_JSON["description"],
        base_health=FIGHTER_JSON["base_health"],
        base_speed=FIGHTER_JSON["base_speed"],
        base_power=FIGHTER_JSON["base_power"],
        technique_ids=FIGHTER_JSON["technique_ids"],
        exclusive_technique_ids=FIGHTER_JSON["exclusive_technique_ids"],
        panoply={BodySlot(k): v for k, v in FIGHTER_JSON["panoply"].items()}
    )
    assert fighter.id == "thorn"
    assert fighter.name == "Thorn"
    assert fighter.base_health == 5
    assert len(fighter.technique_ids) == 8
    assert len(fighter.exclusive_technique_ids) == 2
    assert BodySlot.HEAD in fighter.panoply


def test_load_fighter_from_json_file():
    """load_fighter should load a FighterData from a JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(FIGHTER_JSON, f)
        temp_path = f.name

    try:
        fighter = load_fighter(temp_path)
        assert fighter.id == "thorn"
        assert fighter.base_speed == 4
        assert fighter.panoply[BodySlot.HANDS] == ["gauntlets_of_might", "grippers_of_steadiness"]
    finally:
        os.unlink(temp_path)


def test_load_all_fighters():
    """load_all_fighters should load all JSON files from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "thorn.json"), "w") as f:
            json.dump(FIGHTER_JSON, f)
        f2 = dict(FIGHTER_JSON, id="ember", name="Ember")
        with open(os.path.join(tmpdir, "ember.json"), "w") as f:
            json.dump(f2, f)

        fighters = load_all_fighters(tmpdir)
        assert len(fighters) == 2
        assert "thorn" in fighters
        assert "ember" in fighters
        assert fighters["thorn"].name == "Thorn"


def test_load_fighter_missing_file():
    """load_fighter should raise FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        load_fighter("nonexistent_fighter.json")


def test_fighter_data_has_intellect():
    """FighterData should support base_intellect field."""
    fighter = FighterData(
        id="test",
        name="Test",
        description="A test fighter.",
        base_health=5,
        base_speed=4,
        base_power=5,
        base_intellect=6,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={}
    )
    assert fighter.base_intellect == 6


def test_load_fighter_with_intellect():
    """load_fighter should parse base_intellect from JSON."""
    data = dict(FIGHTER_JSON, base_intellect=6)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    try:
        fighter = load_fighter(temp_path)
        assert fighter.base_intellect == 6
    finally:
        os.unlink(temp_path)


def test_load_fighter_intellect_defaults_to_zero():
    """Fighter JSON without base_intellect should default to 0."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(FIGHTER_JSON, f)
        temp_path = f.name
    try:
        fighter = load_fighter(temp_path)
        assert fighter.base_intellect == 0
    finally:
        os.unlink(temp_path)


def test_fighter_feat_id_loads():
    import json, os, tempfile
    from game.fighter import load_fighter
    data = {
        "id": "tester", "name": "Tester", "description": "d",
        "base_health": 5, "base_speed": 4, "base_power": 5, "base_intellect": 3,
        "technique_ids": [], "exclusive_technique_ids": [], "panoply": {},
        "feat_id": "iron_composure",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        fighter = load_fighter(path)
        assert fighter.feat_id == "iron_composure"
    finally:
        os.unlink(path)


def test_fighter_feat_id_defaults_empty():
    import json, os, tempfile
    from game.fighter import load_fighter
    data = {
        "id": "tester", "name": "Tester", "description": "d",
        "base_health": 5, "base_speed": 4, "base_power": 5, "base_intellect": 3,
        "technique_ids": [], "exclusive_technique_ids": [], "panoply": {},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        fighter = load_fighter(path)
        assert fighter.feat_id == ""
    finally:
        os.unlink(path)
