"""Tests for item data model and loader."""
import json
import os
import tempfile
import pytest
from game.item import ItemData, ItemBuff, ItemReactive, load_item, load_all_items
from game.enums import BodySlot, BuffType


ITEM_JSON = {
    "id": "iron_helm",
    "name": "Iron Helm",
    "description": "A sturdy helmet that provides solid protection.",
    "slot": "head",
    "passive_buffs": [
        {"buff_type": "health", "value": 10},
        {"buff_type": "damage_reduction", "value": 2}
    ],
    "reactive": None
}


def test_item_buff_creation():
    """ItemBuff should hold type and value."""
    buff = ItemBuff(buff_type=BuffType.HEALTH, value=10)
    assert buff.buff_type == BuffType.HEALTH
    assert buff.value == 10


def test_item_reactive_creation():
    """ItemReactive should describe an automatic trigger."""
    reactive = ItemReactive(trigger="when_struck", effect="counter_damage", value=5)
    assert reactive.trigger == "when_struck"
    assert reactive.value == 5


def test_item_data_no_reactive():
    """ItemData should handle items without reactive effects."""
    item = ItemData(
        id="iron_helm",
        name="Iron Helm",
        description="Sturdy helmet.",
        slot=BodySlot.HEAD,
        passive_buffs=[ItemBuff(BuffType.HEALTH, 10)],
        reactive=None
    )
    assert item.slot == BodySlot.HEAD
    assert len(item.passive_buffs) == 1
    assert item.reactive is None


def test_load_item_from_json():
    """load_item should parse a JSON file into ItemData."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ITEM_JSON, f)
        temp_path = f.name

    try:
        item = load_item(temp_path)
        assert item.id == "iron_helm"
        assert item.slot == BodySlot.HEAD
        assert len(item.passive_buffs) == 2
        assert item.passive_buffs[0].buff_type == BuffType.HEALTH
        assert item.reactive is None
    finally:
        os.unlink(temp_path)


def test_load_all_items():
    """load_all_items should load all item JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "iron_helm.json"), "w") as f:
            json.dump(ITEM_JSON, f)
        i2 = dict(ITEM_JSON, id="crown_of_resolve", name="Crown of Resolve")
        with open(os.path.join(tmpdir, "crown_of_resolve.json"), "w") as f:
            json.dump(i2, f)

        items = load_all_items(tmpdir)
        assert len(items) == 2
        assert "iron_helm" in items
        assert "crown_of_resolve" in items


def test_item_buff_with_scales_with():
    """ItemBuff should support optional scales_with field."""
    buff = ItemBuff(buff_type=BuffType.POWER, value=1, scales_with="intellect")
    assert buff.scales_with == "intellect"
    assert buff.value == 1  # base value, scaling applied at combat time


def test_load_item_with_scales_with():
    """load_item should parse scales_with from JSON."""
    data = dict(ITEM_JSON)
    data["passive_buffs"] = [
        {"buff_type": "power", "value": 1, "scales_with": "intellect"}
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    try:
        item = load_item(temp_path)
        assert item.passive_buffs[0].scales_with == "intellect"
    finally:
        os.unlink(temp_path)


def test_load_item_buff_without_scales_with():
    """ItemBuff without scales_with in JSON should default to None."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ITEM_JSON, f)
        temp_path = f.name
    try:
        item = load_item(temp_path)
        assert item.passive_buffs[0].scales_with is None
    finally:
        os.unlink(temp_path)


def test_resolve_item_conflict_rings_allow_two():
    from game.enums import BodySlot
    from game.item import ItemData, resolve_item_conflict
    items = {
        "r1": ItemData("r1", "R1", "", BodySlot.RING, []),
        "r2": ItemData("r2", "R2", "", BodySlot.RING, []),
        "r3": ItemData("r3", "R3", "", BodySlot.RING, []),
        "h1": ItemData("h1", "H1", "", BodySlot.HEAD, []),
        "h2": ItemData("h2", "H2", "", BodySlot.HEAD, []),
    }
    assert resolve_item_conflict(["r1"], "r2", items) is None
    assert resolve_item_conflict(["r1", "r2"], "r3", items) == "r1"
    assert resolve_item_conflict(["h1"], "h2", items) == "h1"
    assert resolve_item_conflict([], "h1", items) is None
