"""Validation tests for the 12-fighter roster and its exclusive techniques."""
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items

EXCLUSIVES = [
    "rending_flurry", "executioners_gambit", "avalanche", "plunging_talon",
    "vanishing_cut", "windward_veil", "immolating_insight", "labyrinth_of_mirrors",
    "prescient_guard", "juggernaut_blow", "retribution_guard", "aegis_wall",
]


def test_exclusive_techniques_present_and_valid():
    techs = load_all_techniques("game/data/techniques")
    for tid in EXCLUSIVES:
        assert tid in techs, tid
    assert techs["juggernaut_blow"].effects.health_damage_scale == 1
    assert techs["retribution_guard"].effects.health_damage_scale == 1
    assert techs["aegis_wall"].effects.health_damage_reduction == 1
    assert techs["plunging_talon"].effects.speed_diff_scale == 1
    assert techs["vanishing_cut"].effects.speed_damage_scale == 1
    assert techs["immolating_insight"].effects.intellect_damage_scale == 1
    assert techs["prescient_guard"].effects.intellect_damage_reduction == 1
    assert techs["avalanche"].base_action.value == "charge"
