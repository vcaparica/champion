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
