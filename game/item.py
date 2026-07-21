"""
game/item.py - Item data model for Champion
============================================
Defines ItemData, ItemBuff, and ItemReactive dataclasses with JSON loading.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional
from game.enums import BodySlot, BuffType


@dataclass
class ItemBuff:
    """A passive stat modification from an item."""
    buff_type: BuffType
    value: int
    scales_with: Optional[str] = None


@dataclass
class ItemReactive:
    """An automatic trigger effect on an item."""
    trigger: str
    effect: str
    value: int


@dataclass
class ItemData:
    """Complete data for a single item."""
    id: str
    name: str
    description: str
    slot: BodySlot
    passive_buffs: list[ItemBuff]
    reactive: Optional[ItemReactive] = None


def load_item(filepath: str) -> ItemData:
    """Load a single item from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_item(data)


def load_all_items(directory: str) -> dict[str, ItemData]:
    """Load all item JSON files from a directory."""
    items = {}
    if not os.path.isdir(directory):
        return items
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            path = os.path.join(directory, filename)
            item = load_item(path)
            items[item.id] = item
    return items


def _dict_to_item(data: dict) -> ItemData:
    """Convert a raw JSON dict to an ItemData instance."""
    buffs = []
    for b in data.get("passive_buffs", []):
        buffs.append(ItemBuff(
            buff_type=BuffType(b["buff_type"]),
            value=b["value"],
            scales_with=b.get("scales_with")
        ))

    reactive = None
    if data.get("reactive"):
        r = data["reactive"]
        reactive = ItemReactive(trigger=r["trigger"], effect=r["effect"], value=r.get("value", 0))

    return ItemData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        slot=BodySlot(data["slot"]),
        passive_buffs=buffs,
        reactive=reactive,
    )
