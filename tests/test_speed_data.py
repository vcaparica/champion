"""Tests that the new Speed techniques and items exist and parse."""
import os
from game.technique import load_all_techniques
from game.item import load_all_items
from game.enums import BuffType

TECH_DIR = os.path.join("game", "data", "techniques")
ITEM_DIR = os.path.join("game", "data", "items")

NEW_TECHS = ["tempo_strike", "blitz", "momentum_edge",
             "quickened_guard", "riposte_in_a_blink", "slipstream"]


def test_new_speed_techniques_load():
    techs = load_all_techniques(TECH_DIR)
    for tid in NEW_TECHS:
        assert tid in techs, tid
    assert techs["tempo_strike"].effects.speed_instead_of_power is True
    assert techs["blitz"].effects.speed_damage_scale == 1
    assert techs["momentum_edge"].effects.speed_diff_scale == 1
    assert techs["quickened_guard"].effects.speed_damage_reduction == 1
    assert techs["riposte_in_a_blink"].effects.require_speed_advantage is True
    assert techs["riposte_in_a_blink"].effects.damage_modifier == 3
    assert techs["slipstream"].effects.require_speed_advantage is True
    assert techs["slipstream"].effects.apply_debuff == "slowed"
