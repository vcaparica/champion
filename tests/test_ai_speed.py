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
    from game.ai import SPEED_RELIANT_TECHNIQUES
    boulder = FighterInstance(fighter_data=FIGHTERS["boulder"])  # speed 4 (< 5, filter applies)
    pool = boulder.fighter_data.technique_ids
    speed_reliant_in_pool = [t for t in pool if t in SPEED_RELIANT_TECHNIQUES]
    # Guard against the assertion going vacuous: if the pool ever stops carrying a
    # speed-reliant technique, this test would pass without exercising the filter.
    assert speed_reliant_in_pool, "boulder's pool must contain a speed-reliant technique for this test to mean anything"
    # boulder picks base_intellect (2) of 7, with 6 non-speed alternatives, so the
    # filter can and must drop every speed-reliant technique. Selection is random,
    # so repeat: with the filter working a speed-reliant pick is impossible, so many
    # draws still yield none; without it, each draw would include one ~29% of the time.
    for _ in range(50):
        picks = choose_ai_techniques(boulder, TECHS)
        for tid in speed_reliant_in_pool:
            assert tid not in picks, f"slow fighter should not pick speed-reliant {tid}"
