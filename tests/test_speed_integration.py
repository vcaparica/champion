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
    zephyr = FighterInstance(
        fighter_data=FIGHTERS["zephyr"],
        selected_techniques=["tempo_strike", "slipstream"],
        selected_items=["swiftedge_ring", "reflex_bracers", "livewire_vest"],
    )
    apply_buffs(zephyr, ITEMS)
    # 3 items -> effective speed 7 - 2 = 5
    assert get_effective_speed(zephyr) == 5

    brutus = FighterInstance(
        fighter_data=FIGHTERS["brutus"],
        selected_items=["brute_plate"],
    )
    apply_buffs(brutus, ITEMS)

    res = resolve_exchange(
        zephyr, brutus, ActionType.STRIKE, ActionType.FEINT,
        attacker_technique=TECHS["tempo_strike"],
    )
    # Tempo Strike deals damage = Zephyr's effective speed (5), before Brutus DR.
    assert res.outcome == "hit"
    assert res.damage_to_defender >= 1


def test_speed_diff_items_from_data_reduce_damage():
    # Zephyr equips Aegis of Winds (speed-diff reduction) and is much faster than Brutus.
    zephyr = FighterInstance(
        fighter_data=FIGHTERS["zephyr"],
        selected_items=["aegis_of_winds"],
    )
    apply_buffs(zephyr, ITEMS)
    brutus = FighterInstance(fighter_data=FIGHTERS["brutus"])

    # Brutus strikes, Zephyr feints: FEINT vs STRIKE -> hit, damage_to_attacker (Zephyr) takes d_damage.
    guarded = resolve_exchange(zephyr, brutus, ActionType.FEINT, ActionType.STRIKE)
    plain_zephyr = FighterInstance(fighter_data=FIGHTERS["zephyr"], selected_items=["cape_of_the_zephyr"])
    apply_buffs(plain_zephyr, ITEMS)
    plain = resolve_exchange(plain_zephyr, brutus, ActionType.FEINT, ActionType.STRIKE)
    assert guarded.damage_to_attacker <= plain.damage_to_attacker
