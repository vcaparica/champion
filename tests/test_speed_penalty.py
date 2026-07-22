"""Tests for the item-count Speed penalty."""
from game.combat import FighterInstance, get_effective_speed, item_speed_penalty
from game.fighter import FighterData


def mk(speed, items=None):
    data = FighterData(
        id="t", name="T", description="",
        base_health=5, base_speed=speed, base_power=5, base_intellect=4,
        technique_ids=[], exclusive_technique_ids=[], panoply={},
    )
    return FighterInstance(fighter_data=data, selected_items=list(items or []))


def test_item_speed_penalty_first_item_free():
    assert item_speed_penalty(0) == 0
    assert item_speed_penalty(1) == 0
    assert item_speed_penalty(2) == 1
    assert item_speed_penalty(4) == 3


def test_effective_speed_drops_with_items():
    assert get_effective_speed(mk(7, ["a", "b", "c"])) == 5  # 7 - (3-1)


def test_effective_speed_floor_at_1():
    assert get_effective_speed(mk(2, ["a", "b", "c", "d"])) == 1


def test_effective_speed_dynamic_on_item_change():
    inst = mk(6, ["a", "b", "c"])
    assert get_effective_speed(inst) == 4
    inst.selected_items.pop()
    assert get_effective_speed(inst) == 5
    inst.selected_items.append("x")
    assert get_effective_speed(inst) == 4


def test_losing_only_free_item_no_speed_gain():
    inst = mk(5, ["a"])
    assert get_effective_speed(inst) == 5
    inst.selected_items.pop()
    assert get_effective_speed(inst) == 5


def test_reset_then_reapply_restores_item_buffs():
    from game.combat import apply_buffs
    from game.item import ItemData, ItemBuff
    from game.enums import BuffType, BodySlot
    from game.match import MatchState, reset_for_new_round

    boots = ItemData(id="b", name="B", description="", slot=BodySlot.FEET,
                     passive_buffs=[ItemBuff(BuffType.POWER, 2)])
    inst = mk(5, ["b"])
    apply_buffs(inst, {"b": boots})
    assert inst.power_modifier == 2

    match = MatchState(team_a=[inst], team_b=[])
    reset_for_new_round(match)
    assert inst.power_modifier == 0  # reset cleared the modifier

    for f in match.team_a + match.team_b:
        apply_buffs(f, {"b": boots})
    assert inst.power_modifier == 2  # re-applied for the new round
