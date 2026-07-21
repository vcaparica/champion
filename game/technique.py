"""
game/technique.py - Technique data model for Champion
======================================================
Defines TechniqueData and TechniqueEffect dataclasses with JSON loading.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
from game.enums import ActionType


@dataclass
class TechniqueEffect:
    """Modifiers applied when a technique is used."""
    damage_modifier: int = 0
    bypass_range: bool = False
    heal_on_hit: int = 0
    reposition_to: Optional[str] = None
    apply_debuff: Optional[str] = None
    steal_item: bool = False
    switch_own_item: bool = False
    gain_advantage: Optional[str] = None
    multi_target: bool = False
    intellect_damage_scale: int = 0
    opponent_intellect_scale: int = 0
    intellect_to_speed: bool = False
    intellect_damage_reduction: int = 0
    require_intellect_advantage: bool = False


@dataclass
class TechniqueData:
    """Complete data for a single technique."""
    id: str
    name: str
    description: str
    base_action: ActionType
    effects: TechniqueEffect
    predictability_increase: int = 1


def load_technique(filepath: str) -> TechniqueData:
    """Load a single technique from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_technique(data)


def load_all_techniques(directory: str) -> dict[str, TechniqueData]:
    """Load all technique JSON files from a directory."""
    techniques = {}
    if not os.path.isdir(directory):
        return techniques
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            path = os.path.join(directory, filename)
            tech = load_technique(path)
            techniques[tech.id] = tech
    return techniques


def _dict_to_technique(data: dict) -> TechniqueData:
    """Convert a raw JSON dict to a TechniqueData instance."""
    effects_raw = data.get("effects", {})
    effects = TechniqueEffect(
        damage_modifier=effects_raw.get("damage_modifier", 0),
        bypass_range=effects_raw.get("bypass_range", False),
        heal_on_hit=effects_raw.get("heal_on_hit", 0),
        reposition_to=effects_raw.get("reposition_to"),
        apply_debuff=effects_raw.get("apply_debuff"),
        steal_item=effects_raw.get("steal_item", False),
        switch_own_item=effects_raw.get("switch_own_item", False),
        gain_advantage=effects_raw.get("gain_advantage"),
        multi_target=effects_raw.get("multi_target", False),
        intellect_damage_scale=effects_raw.get("intellect_damage_scale", 0),
        opponent_intellect_scale=effects_raw.get("opponent_intellect_scale", 0),
        intellect_to_speed=effects_raw.get("intellect_to_speed", False),
        intellect_damage_reduction=effects_raw.get("intellect_damage_reduction", 0),
        require_intellect_advantage=effects_raw.get("require_intellect_advantage", False),
    )
    return TechniqueData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        base_action=ActionType(data["base_action"]),
        effects=effects,
        predictability_increase=data.get("predictability_increase", 1),
    )
