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
    # Retribution Guard (Ward's block exclusive): absorbs like Aegis Wall but
    # seizes offensive advantage, keeping the two exclusives mechanically distinct.
    assert techs["retribution_guard"].effects.health_damage_reduction == 1
    assert techs["retribution_guard"].effects.gain_advantage == "offensive"
    assert techs["aegis_wall"].effects.health_damage_reduction == 1
    assert techs["plunging_talon"].effects.speed_diff_scale == 1
    assert techs["vanishing_cut"].effects.speed_damage_scale == 1
    assert techs["immolating_insight"].effects.intellect_damage_scale == 1
    # Prescient Guard (Cipher's assess exclusive): reveals an unused technique
    # and marks a weak spot for the next counter.
    assert techs["prescient_guard"].effects.assess_reveal_unused_technique is True
    assert techs["prescient_guard"].effects.assess_next_counter_bonus == 2
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


FEAT_BY_FIGHTER = {
    "aegis": "iron_composure", "anvil": "unbroken_stand", "ward": "warding_gale",
    "boulder": "relentless_momentum", "razor": "bladestorm", "talon": "lethal_calculus",
    "cloud": "drift_untouched", "falcon": "falcons_stoop", "whisper": "silent_vanish",
    "cipher": "everything_foreseen", "ember": "cinderbrand", "mirage": "hall_of_mirrors",
}

VALID_TRIGGERS = {"round_start", "exchange_start", "deal_damage", "take_damage",
                  "defense_success", "low_health", "would_fall"}
VALID_EFFECTS = {"reduce_incoming", "negate_incoming", "bonus_outgoing", "reflect",
                 "damage_reduction_lasting", "power_lasting", "heal", "cheat_death",
                 "gain_advantage", "reduce_predictability", "apply_debuff", "apply_burn",
                 "reposition"}


def test_all_feats_present_and_valid():
    from game.feat import load_all_feats
    feats = load_all_feats("game/data/feats")
    assert len(feats) == 12
    for fid, feat in feats.items():
        assert " | " in feat.description, f"{fid} description missing mechanics separator"
        assert feat.reactions, f"{fid} has no reactions"
        for r in feat.reactions:
            assert r.trigger in VALID_TRIGGERS, f"{fid}: bad trigger {r.trigger}"
            assert r.effect in VALID_EFFECTS, f"{fid}: bad effect {r.effect}"


def test_every_fighter_references_its_feat():
    from game.fighter import load_all_fighters
    from game.feat import load_all_feats
    fighters = load_all_fighters("game/data/fighters")
    feats = load_all_feats("game/data/feats")
    for fid, expected_feat in FEAT_BY_FIGHTER.items():
        assert fighters[fid].feat_id == expected_feat, fid
        assert expected_feat in feats, expected_feat


def test_feats_attach_and_fire_end_to_end():
    from game.fighter import load_all_fighters
    from game.feat import load_all_feats
    from game.item import load_all_items
    from game.combat import FighterInstance, resolve_exchange
    from game.reactions import attach_reactions
    from game.enums import ActionType
    fighters = load_all_fighters("game/data/fighters")
    feats = load_all_feats("game/data/feats")
    items = load_all_items("game/data/items")
    # Talon's Lethal Calculus adds opponent predictability to a landed hit.
    # The foe is left UNATTACHED so no defensive Feat (e.g. Cloud's Drift) distorts the number.
    talon = FighterInstance(fighter_data=fighters["talon"])
    attach_reactions(talon, feats, items)
    foe = FighterInstance(fighter_data=fighters["cloud"])
    foe.predictability = 2
    baseline = resolve_exchange(
        FighterInstance(fighter_data=fighters["talon"]),
        FighterInstance(fighter_data=fighters["cloud"]),
        ActionType.STRIKE, ActionType.FEINT,
    ).damage_to_defender
    boosted = resolve_exchange(talon, foe, ActionType.STRIKE, ActionType.FEINT).damage_to_defender
    assert boosted == baseline + 2


def test_item_reactive_fires_end_to_end():
    from game.fighter import load_all_fighters
    from game.feat import load_all_feats
    from game.item import load_all_items
    from game.combat import FighterInstance, resolve_exchange
    from game.reactions import attach_reactions
    from game.enums import ActionType
    fighters = load_all_fighters("game/data/fighters")
    feats = load_all_feats("game/data/feats")
    items = load_all_items("game/data/items")
    # Berserker Vest: when_struck -> +1 power (power_lasting). Talon's panoply includes it.
    talon = FighterInstance(fighter_data=fighters["talon"], selected_items=["berserker_vest"])
    attach_reactions(talon, feats, items)
    before = talon.power_modifier
    foe = FighterInstance(fighter_data=fighters["boulder"])
    # FEINT vs STRIKE: the attacker (Talon) takes the hit, i.e. is struck.
    resolve_exchange(talon, foe, ActionType.FEINT, ActionType.STRIKE)
    assert talon.power_modifier == before + 1
