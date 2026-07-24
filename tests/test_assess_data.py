"""Tests for the new shared techniques added by the Assess data migration."""
from game.technique import load_all_techniques


def _load():
    return load_all_techniques("game/data/techniques")


def test_all_technique_descriptions_use_mechanics_separator():
    t = _load()
    for tid, tech in t.items():
        assert " | " in tech.description, f"{tid} description missing mechanics separator"


def test_assess_pool_loads_with_correct_effects():
    t = _load()
    assert t["read_the_blade"].effects.assess_next_counter_bonus == 3
    assert t["roll_with_the_blow"].effects.assess_next_damage_half is True
    assert t["predict_the_tempo"].effects.assess_speed_buff == 1
    assert t["predict_the_tempo"].effects.assess_speed_buff_volleys == 3
    assert t["pierce_the_trick"].effects.assess_reveal_unused_technique is True
    assert t["eye_for_gear"].effects.assess_reveal_item is True


def test_gap_fill_techniques_scale_correctly():
    t = _load()
    assert t["ironjaw_strike"].base_action.value == "strike"
    assert t["ironjaw_strike"].effects.health_damage_scale == 1
    assert t["false_wound"].base_action.value == "feint"
    assert t["false_wound"].effects.health_damage_scale == 1
    assert t["calculated_charge"].base_action.value == "charge"
    assert t["calculated_charge"].effects.intellect_damage_scale == 1
    assert t["bulldoze"].base_action.value == "charge"
    assert t["bulldoze"].effects.health_damage_scale == 1


def test_repurposed_exclusives_have_new_base_actions():
    t = _load()
    assert t["retribution_guard"].base_action.value == "block"
    assert t["labyrinth_of_mirrors"].base_action.value == "feint"
    assert t["immolating_insight"].base_action.value == "feint"
    assert t["vanishing_cut"].base_action.value == "counter"
    assert t["juggernaut_blow"].base_action.value == "charge"
    assert t["prescient_guard"].base_action.value == "assess"


def test_prescient_guard_and_retribution_guard_effects_redesigned():
    t = _load()
    # Cipher's assess exclusive: reveals an unused technique and marks a weak spot.
    assert t["prescient_guard"].effects.assess_reveal_unused_technique is True
    assert t["prescient_guard"].effects.assess_next_counter_bonus == 2
    # Ward's block exclusive: absorbs like a wall but seizes offensive advantage
    # (distinct from aegis_wall, which takes defensive advantage).
    assert t["retribution_guard"].effects.health_damage_reduction == 1
    assert t["retribution_guard"].effects.gain_advantage == "offensive"
    # Scaling fields preserved on the other repurposed exclusives (still valid in new action).
    assert t["immolating_insight"].effects.intellect_damage_scale == 1
    assert t["vanishing_cut"].effects.speed_damage_scale == 1
    assert t["juggernaut_blow"].effects.health_damage_scale == 1
