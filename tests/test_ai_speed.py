"""Tests for Speed-aware AI item and technique choices."""
import os
from game.ai import choose_ai_items, choose_ai_techniques
from game.combat import FighterInstance
from game.fighter import load_all_fighters
from game.item import load_all_items
from game.technique import load_all_techniques

FIGHTERS = load_all_fighters(os.path.join("game", "data", "fighters"))
ITEMS = load_all_items(os.path.join("game", "data", "items"))
TECHS = load_all_techniques(os.path.join("game", "data", "techniques"))


def test_ai_items_within_cap_and_one_per_slot():
    from collections import Counter
    from game.enums import BodySlot
    for f in FIGHTERS.values():
        inst = FighterInstance(fighter_data=f)
        chosen = choose_ai_items(inst, ITEMS)
        assert 1 <= len(chosen) <= f.base_speed, f.id
        counts = Counter(ITEMS[i].slot for i in chosen)
        for slot, count in counts.items():
            limit = 2 if slot == BodySlot.RING else 1
            assert count <= limit, f"{f.id} equipped {count} items in slot {slot}"


def test_ai_fast_fighter_takes_more_items_than_slow():
    falcon = FighterInstance(fighter_data=FIGHTERS["falcon"])  # speed 6
    cipher = FighterInstance(fighter_data=FIGHTERS["cipher"])  # speed 2
    assert len(choose_ai_items(falcon, ITEMS)) > len(choose_ai_items(cipher, ITEMS))


def test_ai_slow_fighter_avoids_speed_techniques():
    boulder = FighterInstance(fighter_data=FIGHTERS["boulder"])  # speed 4, pool has blitz
    picks = choose_ai_techniques(boulder, TECHS)
    assert "blitz" not in picks
