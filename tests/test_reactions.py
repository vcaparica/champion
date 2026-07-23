"""Unit tests for the reaction engine dispatcher and effects."""
from game.feat import Reaction
from game.fighter import FighterData
from game.combat import FighterInstance
from game.reactions import Trigger, ReactionContext, fire
from game.enums import Advantage, DebuffType


def _inst(reactions=None, **kw):
    fd = FighterData("t", "T", "d",
                     kw.pop("health", 5), kw.pop("speed", 4),
                     kw.pop("power", 5), [], [], {}, base_intellect=kw.pop("intellect", 3))
    inst = FighterInstance(fighter_data=fd)
    inst.reactions = reactions or []
    for k, v in kw.items():
        setattr(inst, k, v)
    return inst


def test_bonus_outgoing_flat():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", value=2)])
    opp = _inst()
    ctx = ReactionContext(me=me, opponent=opp, outgoing_damage=6)
    assert fire(Trigger.DEAL_DAMAGE, ctx) is True
    assert ctx.outgoing_damage == 8


def test_bonus_outgoing_scales_half_speed_ceil():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", scales_with="half_speed")], speed=5)
    ctx = ReactionContext(me=me, opponent=_inst(), outgoing_damage=6)
    fire(Trigger.DEAL_DAMAGE, ctx)
    assert ctx.outgoing_damage == 6 + 3  # ceil(5/2)=3


def test_bonus_outgoing_opponent_predictability_capped():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", scales_with="opponent_predictability", cap=4)])
    opp = _inst(predictability=7)
    ctx = ReactionContext(me=me, opponent=opp, outgoing_damage=6)
    fire(Trigger.DEAL_DAMAGE, ctx)
    assert ctx.outgoing_damage == 6 + 4


def test_speed_advantage_condition_blocks_when_slower():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", value=3, condition="speed_advantage")])
    ctx = ReactionContext(me=me, opponent=_inst(), outgoing_damage=6, speed_advantage=False)
    assert fire(Trigger.DEAL_DAMAGE, ctx) is False
    assert ctx.outgoing_damage == 6


def test_reduce_incoming_floored_at_zero():
    me = _inst([Reaction("take_damage", "reduce_incoming", value=10)])
    ctx = ReactionContext(me=me, opponent=_inst(), incoming_damage=6)
    fire(Trigger.TAKE_DAMAGE, ctx)
    assert ctx.incoming_damage == 0


def test_negate_incoming_once_per_round():
    me = _inst([Reaction("take_damage", "negate_incoming", once_per="round")])
    opp = _inst()
    ctx1 = ReactionContext(me=me, opponent=opp, incoming_damage=6)
    fire(Trigger.TAKE_DAMAGE, ctx1)
    assert ctx1.incoming_damage == 0
    ctx2 = ReactionContext(me=me, opponent=opp, incoming_damage=6)
    fire(Trigger.TAKE_DAMAGE, ctx2)
    assert ctx2.incoming_damage == 6  # consumed for the round


def test_by_technique_condition():
    me = _inst([Reaction("take_damage", "reduce_incoming", scales_with="half_intellect", condition="by_technique")], intellect=6)
    hit_plain = ReactionContext(me=me, opponent=_inst(), incoming_damage=8, by_technique=False)
    fire(Trigger.TAKE_DAMAGE, hit_plain)
    assert hit_plain.incoming_damage == 8
    hit_tech = ReactionContext(me=me, opponent=_inst(), incoming_damage=8, by_technique=True)
    fire(Trigger.TAKE_DAMAGE, hit_tech)
    assert hit_tech.incoming_damage == 8 - 3  # ceil(6/2)=3


def test_damage_reduction_lasting_stacks_to_cap():
    me = _inst([Reaction("take_damage", "damage_reduction_lasting", value=1, max_stacks=3)])
    for _ in range(5):
        fire(Trigger.TAKE_DAMAGE, ReactionContext(me=me, opponent=_inst(), incoming_damage=4))
    assert me.damage_reduction == 3


def test_power_lasting_stacks_to_cap():
    me = _inst([Reaction("deal_damage", "power_lasting", value=1, max_stacks=3)])
    for _ in range(5):
        fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=_inst(), outgoing_damage=4))
    assert me.power_modifier == 3


def test_gain_advantage():
    me = _inst([Reaction("deal_damage", "gain_advantage", advantage="offensive")])
    fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=_inst(), outgoing_damage=4))
    assert me.current_advantage == Advantage.OFFENSIVE


def test_reduce_predictability():
    me = _inst([Reaction("deal_damage", "reduce_predictability", value=2)], predictability=5)
    fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=_inst(), outgoing_damage=4))
    assert me.predictability == 3


def test_apply_debuff_to_opponent():
    me = _inst([Reaction("deal_damage", "apply_debuff", debuff="dazed")])
    opp = _inst()
    fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=opp, outgoing_damage=4))
    assert DebuffType.DAZED in opp.active_debuffs


def test_apply_burn_stacks_on_opponent_capped():
    me = _inst([Reaction("deal_damage", "apply_burn", value=1, max_stacks=3)])
    opp = _inst()
    for _ in range(5):
        fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=opp, outgoing_damage=4))
    assert opp.reaction_state["burn_stacks"] == 3


def test_heal():
    me = _inst([Reaction("low_health", "heal", value=12)])
    me.current_health = 5
    fire(Trigger.LOW_HEALTH, ReactionContext(me=me, opponent=_inst()))
    assert me.current_health == 17


def test_cheat_death_sets_health_and_rider():
    me = _inst([Reaction("would_fall", "cheat_death", once_per="round", rider_power=2)])
    me.current_health = 8
    assert fire(Trigger.WOULD_FALL, ReactionContext(me=me, opponent=_inst())) is True
    assert me.current_health == 1
    assert me.power_modifier == 2
    # Consumed: second would-fall does nothing
    assert fire(Trigger.WOULD_FALL, ReactionContext(me=me, opponent=_inst())) is False


def test_action_avoid_condition():
    me = _inst([Reaction("defense_success", "reflect", value=3, condition="action_avoid")])
    not_avoid = ReactionContext(me=me, opponent=_inst(), action="block")
    assert fire(Trigger.DEFENSE_SUCCESS, not_avoid) is False
    is_avoid = ReactionContext(me=me, opponent=_inst(), action="avoid")
    assert fire(Trigger.DEFENSE_SUCCESS, is_avoid) is True
    assert is_avoid.outgoing_damage == 3


def test_adapter_maps_item_triggers_and_effects():
    from game.item import ItemReactive
    from game.reactions import _adapt_item_reactive
    r = _adapt_item_reactive(ItemReactive("when_struck", "power_boost", 1))
    assert r.trigger == "take_damage"
    assert r.effect == "power_lasting"
    assert r.value == 1
    r2 = _adapt_item_reactive(ItemReactive("when_hit_by_technique", "damage_reduction", 5))
    assert r2.trigger == "take_damage"
    assert r2.condition == "by_technique"
    assert r2.effect == "reduce_incoming"
    r3 = _adapt_item_reactive(ItemReactive("when_avoid_success", "gain_advantage", 0))
    assert r3.trigger == "defense_success"
    assert r3.condition == "action_avoid"
    assert r3.advantage == "offensive"
    r4 = _adapt_item_reactive(ItemReactive("when_low_health", "heal", 12))
    assert r4.trigger == "low_health"
    assert r4.effect == "heal"


def test_adapter_returns_none_for_unknown():
    from game.item import ItemReactive
    from game.reactions import _adapt_item_reactive
    assert _adapt_item_reactive(ItemReactive("unknown_trigger", "heal", 1)) is None
    assert _adapt_item_reactive(ItemReactive("when_struck", "unknown_effect", 1)) is None


def test_attach_reactions_combines_feat_and_items():
    from game.feat import Feat, Reaction
    from game.item import ItemData, ItemReactive
    from game.fighter import FighterData
    from game.combat import FighterInstance
    from game.reactions import attach_reactions
    feats = {"iron_composure": Feat("iron_composure", "Iron Composure", "d",
                                    [Reaction("take_damage", "damage_reduction_lasting", value=1, max_stacks=3)])}
    items = {"berserker_vest": ItemData("berserker_vest", "Berserker Vest", "d",
                                        None, [], ItemReactive("when_struck", "power_boost", 1))}
    fd = FighterData("aegis", "Aegis", "d", 6, 3, 3, [], [], {}, base_intellect=5, feat_id="iron_composure")
    inst = FighterInstance(fighter_data=fd, selected_items=["berserker_vest"])
    attach_reactions(inst, feats, items)
    assert inst.feat.id == "iron_composure"
    assert len(inst.reactions) == 2
    assert inst.reactions[0].effect == "damage_reduction_lasting"
    assert inst.reactions[1].effect == "power_lasting"


def test_attach_reactions_no_feat_id_ok():
    from game.fighter import FighterData
    from game.combat import FighterInstance
    from game.reactions import attach_reactions
    fd = FighterData("x", "X", "d", 5, 4, 5, [], [], {})
    inst = FighterInstance(fighter_data=fd)
    attach_reactions(inst, {}, {})
    assert inst.feat is None
    assert inst.reactions == []
