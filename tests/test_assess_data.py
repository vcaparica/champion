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


def test_executioners_gambit_uses_defender_honored_damage():
    """Talon is the slowest fighter, so its exclusive counter is used almost
    always from the defender side. Its effects must be ones the defender role
    honors -- damage, not the debuff the defender block drops."""
    t = _load()
    eff = t["executioners_gambit"].effects
    assert t["executioners_gambit"].base_action.value == "counter"
    assert eff.damage_modifier == 2
    assert eff.health_damage_scale == 1
    # The old debuff was inert on a slow defender (and in local play); it must be gone.
    assert eff.apply_debuff is None


from game.fighter import load_all_fighters
from game.enums import ActionType


EXPECTED = {
    "razor": (["rending_flurry", "iron_discipline", "momentum_edge", "blazing_counter", "skull_splitter", "slipstream", "read_the_blade"], "rending_flurry"),
    "falcon": (["plunging_talon", "iron_discipline", "war_cry", "blazing_counter", "blitz", "slipstream", "predict_the_tempo"], "plunging_talon"),
    "aegis": (["ironjaw_strike", "aegis_wall", "exploit_weakness", "last_stand", "calculated_charge", "fire_dance", "roll_with_the_blow"], "aegis_wall"),
    "ward": (["ironjaw_strike", "retribution_guard", "exploit_weakness", "last_stand", "bulldoze", "slipstream", "predict_the_tempo"], "retribution_guard"),
    "mirage": (["tempo_strike", "iron_discipline", "labyrinth_of_mirrors", "read_the_pattern", "skull_splitter", "slipstream", "eye_for_gear"], "labyrinth_of_mirrors"),
    "ember": (["mind_over_matter", "defensive_stance", "immolating_insight", "read_the_pattern", "skull_splitter", "fire_dance", "pierce_the_trick"], "immolating_insight"),
    "talon": (["bone_crusher", "iron_discipline", "exploit_weakness", "executioners_gambit", "skull_splitter", "fire_dance", "roll_with_the_blow"], "executioners_gambit"),
    "whisper": (["tempo_strike", "iron_discipline", "exploit_weakness", "vanishing_cut", "bulldoze", "slipstream", "predict_the_tempo"], "vanishing_cut"),
    "boulder": (["bone_crusher", "defensive_stance", "false_wound", "blazing_counter", "avalanche", "slipstream", "read_the_blade"], "avalanche"),
    "anvil": (["ironjaw_strike", "defensive_stance", "war_cry", "last_stand", "juggernaut_blow", "mental_alacrity", "read_the_blade"], "juggernaut_blow"),
    "cipher": (["mind_over_matter", "iron_discipline", "exploit_weakness", "last_stand", "bulldoze", "slipstream", "prescient_guard"], "prescient_guard"),
    "cloud": (["tempo_strike", "defensive_stance", "exploit_weakness", "last_stand", "blitz", "windward_veil", "predict_the_tempo"], "windward_veil"),
}


def test_fighter_pools_match_master_assignment():
    fighters = load_all_fighters("game/data/fighters")
    for fid, (ids, excl) in EXPECTED.items():
        f = fighters[fid]
        assert set(f.technique_ids) == set(ids), fid
        assert f.exclusive_technique_ids == [excl], fid


def test_every_fighter_has_one_technique_per_action():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    all_actions = {a.value for a in ActionType}
    for fid, f in fighters.items():
        actions = sorted(techniques[tid].base_action.value for tid in f.technique_ids)
        assert actions == sorted(all_actions), f"{fid}: {actions}"


def test_exclusive_action_distribution_is_2_2_2_2_2_1_1():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    counts = {}
    for f in fighters.values():
        excl_id = f.exclusive_technique_ids[0]
        action = techniques[excl_id].base_action.value
        counts[action] = counts.get(action, 0) + 1
    assert counts == {"strike": 2, "block": 2, "feint": 2, "counter": 2,
                      "charge": 2, "assess": 1, "avoid": 1}, counts
