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
    min_speed: Optional[int] = None


@dataclass
class ItemReactive:
    """An automatic trigger effect on an item."""
    trigger: str
    effect: str
    value: int
    max_stacks: Optional[int] = None


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


def resolve_item_conflict(selected_ids, new_id, items):
    """Return the id of an already-selected item that equipping new_id displaces, or None.

    Rings are hand-agnostic: up to two may be worn, so a new ring displaces the oldest
    ring only once two are already equipped. Every other slot holds a single item, which
    the new item replaces."""
    new_item = items[new_id]
    if new_item.slot == BodySlot.RING:
        worn_rings = [sid for sid in selected_ids if items[sid].slot == BodySlot.RING]
        return worn_rings[0] if len(worn_rings) >= 2 else None
    for sid in selected_ids:
        if items[sid].slot == new_item.slot:
            return sid
    return None


def _dict_to_item(data: dict) -> ItemData:
    """Convert a raw JSON dict to an ItemData instance."""
    buffs = []
    for b in data.get("passive_buffs", []):
        buffs.append(ItemBuff(
            buff_type=BuffType(b["buff_type"]),
            value=b["value"],
            scales_with=b.get("scales_with"),
            min_speed=b.get("min_speed"),
        ))

    reactive = None
    if data.get("reactive"):
        r = data["reactive"]
        reactive = ItemReactive(trigger=r["trigger"], effect=r["effect"],
                                value=r.get("value", 0), max_stacks=r.get("max_stacks"))

    return ItemData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        slot=BodySlot(data["slot"]),
        passive_buffs=buffs,
        reactive=reactive,
    )
