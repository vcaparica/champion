"""Tests for phase-ordered apply_buffs with Speed scaling."""
from game.combat import FighterInstance, apply_buffs
from game.fighter import FighterData
from game.item import ItemData, ItemBuff
from game.enums import BuffType, BodySlot


def mk(speed, items):
    data = FighterData(id="t", name="T", description="", base_health=5,
                       base_speed=speed, base_power=5, base_intellect=4,
                       technique_ids=[], exclusive_technique_ids=[], panoply={})
    return FighterInstance(fighter_data=data, selected_items=list(items))


def item(iid, slot, buffs):
    return ItemData(id=iid, name=iid, description="", slot=slot, passive_buffs=buffs)


def test_speed_half_scaling():
    ring = item("ring", BodySlot.RING, [ItemBuff(BuffType.POWER, 1, scales_with="speed_half")])
    inst = mk(6, ["ring"])  # 1 item, no penalty, speed 6 -> half = 3
    apply_buffs(inst, {"ring": ring})
    assert inst.power_modifier == 3


def test_full_speed_scaling_health():
    vest = item("vest", BodySlot.ARMOR, [ItemBuff(BuffType.HEALTH, 2, scales_with="speed")])
    inst = mk(7, ["vest"])  # speed 7 -> +14 HP
    start = inst.current_health
    apply_buffs(inst, {"vest": vest})
    assert inst.current_health == start + 14


def test_min_speed_gate_applies_when_fast():
    boots = item("qb", BodySlot.FEET, [ItemBuff(BuffType.POWER, 2, min_speed=5)])
    inst = mk(6, ["qb"])
    apply_buffs(inst, {"qb": boots})
    assert inst.power_modifier == 2


def test_min_speed_gate_blocks_when_slow():
    boots = item("qb", BodySlot.FEET, [ItemBuff(BuffType.POWER, 2, min_speed=5)])
    inst = mk(4, ["qb"])
    apply_buffs(inst, {"qb": boots})
    assert inst.power_modifier == 0


def test_speed_diff_buff_types_set_instance_fields():
    sash = item("sash", BodySlot.WAIST, [ItemBuff(BuffType.SPEED_DIFF_DAMAGE, 1)])
    aegis = item("aegis", BodySlot.CLOTHING, [ItemBuff(BuffType.SPEED_DIFF_REDUCTION, 1)])
    inst = mk(5, ["sash", "aegis"])
    apply_buffs(inst, {"sash": sash, "aegis": aegis})
    assert inst.speed_diff_damage_bonus == 1
    assert inst.speed_diff_damage_reduction == 1


def test_gate_uses_settled_speed_order_independent():
    # base 6, +1 flat speed, 2 items (-1 penalty) => effective 6; min_speed 6 passes in any order.
    boots = item("fb", BodySlot.FEET, [ItemBuff(BuffType.SPEED, 1)])
    gated = item("g", BodySlot.RING, [ItemBuff(BuffType.POWER, 2, min_speed=6)])
    items = {"fb": boots, "g": gated}
    for order in (["fb", "g"], ["g", "fb"]):
        inst = mk(6, order)
        apply_buffs(inst, items)
        assert inst.power_modifier == 2
