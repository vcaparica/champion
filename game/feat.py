"""
game/feat.py - Feat data model for Champion
============================================
An innate, non-selectable passive ability, one per fighter. A Feat owns a list
of Reactions (trigger + effect) resolved by game/reactions.py during combat.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Reaction:
    """A single trigger-to-effect rule owned by a Feat (or adapted from an item)."""
    trigger: str
    effect: str
    value: int = 0
    scales_with: Optional[str] = None
    condition: Optional[str] = None
    once_per: Optional[str] = None
    max_stacks: Optional[int] = None
    cap: Optional[int] = None
    advantage: Optional[str] = None
    debuff: Optional[str] = None
    range: Optional[str] = None
    rider_power: int = 0


@dataclass
class Feat:
    """A fighter's innate passive ability."""
    id: str
    name: str
    description: str
    reactions: list = field(default_factory=list)


def _dict_to_reaction(d: dict) -> Reaction:
    return Reaction(
        trigger=d["trigger"],
        effect=d["effect"],
        value=d.get("value", 0),
        scales_with=d.get("scales_with"),
        condition=d.get("condition"),
        once_per=d.get("once_per"),
        max_stacks=d.get("max_stacks"),
        cap=d.get("cap"),
        advantage=d.get("advantage"),
        debuff=d.get("debuff"),
        range=d.get("range"),
        rider_power=d.get("rider_power", 0),
    )


def _dict_to_feat(data: dict) -> Feat:
    reactions = [_dict_to_reaction(r) for r in data.get("reactions", [])]
    return Feat(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        reactions=reactions,
    )


def load_feat(filepath: str) -> Feat:
    """Load a single Feat from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return _dict_to_feat(json.load(f))


def load_all_feats(directory: str) -> dict:
    """Load all Feat JSON files from a directory. Returns dict keyed by feat id."""
    feats = {}
    if not os.path.isdir(directory):
        return feats
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            feat = load_feat(os.path.join(directory, filename))
            feats[feat.id] = feat
    return feats
