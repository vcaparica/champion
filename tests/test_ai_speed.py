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
    for f in FIGHTERS.values():
        inst = FighterInstance(fighter_data=f)
        chosen = choose_ai_items(inst, ITEMS)
        assert 1 <= len(chosen) <= f.base_speed, f.id
        slots = [ITEMS[i].slot for i in chosen]
        assert len(slots) == len(set(slots)), f"{f.id} equipped two items in one slot"


def test_ai_fast_fighter_takes_more_items_than_slow():
    zephyr = FighterInstance(fighter_data=FIGHTERS["zephyr"])  # speed 7
    brutus = FighterInstance(fighter_data=FIGHTERS["brutus"])  # speed 2
    assert len(choose_ai_items(zephyr, ITEMS)) > len(choose_ai_items(brutus, ITEMS))


def test_ai_slow_fighter_avoids_speed_techniques():
    brutus = FighterInstance(fighter_data=FIGHTERS["brutus"])  # speed 2
    picks = choose_ai_techniques(brutus, TECHS)
    assert "tempo_strike" not in picks
    assert "blitz" not in picks
    assert "momentum_edge" not in picks
