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


def test_new_roster_valid():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")
    expected = {"razor", "talon", "boulder", "falcon", "whisper", "cloud",
                "ember", "mirage", "cipher", "anvil", "ward", "aegis"}
    assert set(fighters) == expected
    for f in fighters.values():
        total = f.base_health + f.base_speed + f.base_power + f.base_intellect
        assert total == 17, f"{f.id} sums to {total}"
        for v in (f.base_health, f.base_speed, f.base_power, f.base_intellect):
            assert 2 <= v <= 6, f"{f.id} has out-of-range attr {v}"
        assert len(f.technique_ids) == 7, f.id
        assert len(f.exclusive_technique_ids) == 1, f.id
        assert f.exclusive_technique_ids[0] in f.technique_ids, f.id
        for tid in f.technique_ids:
            assert tid in techniques, f"{f.id}: missing technique {tid}"
        item_ids = [iid for ids in f.panoply.values() for iid in ids]
        assert len(item_ids) == 7, f"{f.id} has {len(item_ids)} items"
        for iid in item_ids:
            assert iid in items, f"{f.id}: missing item {iid}"
