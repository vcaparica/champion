"""End-to-end check of a fast fighter running a Speed build."""
import os
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.combat import FighterInstance, apply_buffs, get_effective_speed, resolve_exchange
from game.enums import ActionType

FIGHTERS = load_all_fighters(os.path.join("game", "data", "fighters"))
TECHS = load_all_techniques(os.path.join("game", "data", "techniques"))
ITEMS = load_all_items(os.path.join("game", "data", "items"))


def test_fast_fighter_speed_build_volley():
    falcon = FighterInstance(
        fighter_data=FIGHTERS["falcon"],
        selected_techniques=["tempo_strike", "slipstream"],
        selected_items=["swiftedge_ring", "reflex_bracers", "livewire_vest"],
    )
    apply_buffs(falcon, ITEMS)
    # base speed 6, 3 items -> penalty 2, no flat-speed items -> 6 - 2 = 4
    assert get_effective_speed(falcon) == 4

    cipher = FighterInstance(
        fighter_data=FIGHTERS["cipher"],
        selected_items=["brute_plate"],
    )
    apply_buffs(cipher, ITEMS)

    res = resolve_exchange(
        falcon, cipher, ActionType.STRIKE, ActionType.FEINT,
        attacker_technique=TECHS["tempo_strike"],
    )
    # Tempo Strike deals damage = Falcon's effective speed, before Cipher DR.
    assert res.outcome == "hit"
    assert res.damage_to_defender >= 1


def test_speed_diff_items_from_data_reduce_damage():
    falcon = FighterInstance(
        fighter_data=FIGHTERS["falcon"],
        selected_items=["aegis_of_winds"],
    )
    apply_buffs(falcon, ITEMS)
    cipher = FighterInstance(fighter_data=FIGHTERS["cipher"])

    guarded = resolve_exchange(falcon, cipher, ActionType.FEINT, ActionType.STRIKE)
    plain_falcon = FighterInstance(fighter_data=FIGHTERS["falcon"], selected_items=["cape_of_the_zephyr"])
    apply_buffs(plain_falcon, ITEMS)
    plain = resolve_exchange(plain_falcon, cipher, ActionType.FEINT, ActionType.STRIKE)
    assert guarded.damage_to_attacker <= plain.damage_to_attacker
