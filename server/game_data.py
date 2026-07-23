"""
server/game_data.py - Server-side game data registry
======================================================
Loads the shared game data (fighters, techniques, items, feats) once so the
server can build fighter instances and resolve combat authoritatively.
"""
import os
from dataclasses import dataclass

from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.feat import load_all_feats


@dataclass
class GameData:
    """All static game data the server needs for combat resolution."""
    fighters: dict
    techniques: dict
    items: dict
    feats: dict

    @classmethod
    def load(cls, base_dir: str = "game/data") -> "GameData":
        return cls(
            fighters=load_all_fighters(os.path.join(base_dir, "fighters")),
            techniques=load_all_techniques(os.path.join(base_dir, "techniques")),
            items=load_all_items(os.path.join(base_dir, "items")),
            feats=load_all_feats(os.path.join(base_dir, "feats")),
        )
