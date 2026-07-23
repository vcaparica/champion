"""
game/fighter.py - Fighter data model for Champion
==================================================
Defines FighterData dataclass and JSON loader functions.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional
from game.enums import BodySlot


@dataclass
class FighterData:
    """Complete data for a single fighter."""
    id: str
    name: str
    description: str
    base_health: int
    base_speed: int
    base_power: int
    technique_ids: list[str]
    exclusive_technique_ids: list[str]
    panoply: dict[BodySlot, list[str]]
    base_intellect: int = 0
    feat_id: str = ""


def load_fighter(filepath: str) -> FighterData:
    """Load a single fighter from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_fighter(data)


def load_all_fighters(directory: str) -> dict[str, FighterData]:
    """Load all fighter JSON files from a directory. Returns dict keyed by fighter id."""
    fighters = {}
    if not os.path.isdir(directory):
        return fighters
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            path = os.path.join(directory, filename)
            fighter = load_fighter(path)
            fighters[fighter.id] = fighter
    return fighters


def _dict_to_fighter(data: dict) -> FighterData:
    """Convert a raw JSON dict to a FighterData instance."""
    panoply = {}
    raw_panoply = data.get("panoply", {})
    for slot_name, item_ids in raw_panoply.items():
        slot = BodySlot(slot_name)
        panoply[slot] = item_ids
    return FighterData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        base_health=data["base_health"],
        base_speed=data["base_speed"],
        base_power=data["base_power"],
        base_intellect=data.get("base_intellect", 0),
        technique_ids=data["technique_ids"],
        exclusive_technique_ids=data.get("exclusive_technique_ids", []),
        feat_id=data.get("feat_id", ""),
        panoply=panoply,
    )
