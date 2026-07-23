"""
game/reactions.py - Reactive engine for Champion
=================================================
A small trigger/condition/effect system. Feats and (via an adapter) item
reactives contribute Reaction rules to a FighterInstance's `reactions` list;
`fire()` dispatches them at combat hook points, mutating instances and the
per-hit damage carried on a ReactionContext.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from game.enums import Advantage, DebuffType, Range
from game.combat import get_effective_speed, get_effective_intellect


class Trigger(Enum):
    ROUND_START = "round_start"
    EXCHANGE_START = "exchange_start"
    DEAL_DAMAGE = "deal_damage"
    TAKE_DAMAGE = "take_damage"
    DEFENSE_SUCCESS = "defense_success"
    LOW_HEALTH = "low_health"
    WOULD_FALL = "would_fall"


@dataclass
class ReactionContext:
    me: object
    opponent: object
    incoming_damage: int = 0
    outgoing_damage: int = 0
    by_technique: bool = False
    speed_advantage: bool = False
    action: Optional[str] = None


def _ceil_div(n: int, d: int) -> int:
    return -(-n // d)


def _state(me) -> dict:
    st = me.reaction_state
    st.setdefault("once_round", set())
    st.setdefault("once_volley", set())
    st.setdefault("stacks", {})
    st.setdefault("burn_stacks", 0)
    return st


def _scaled_amount(reaction, me, opponent) -> int:
    sw = reaction.scales_with
    if sw is None:
        return reaction.value
    if sw == "half_speed":
        return _ceil_div(get_effective_speed(me), 2)
    if sw == "speed":
        return get_effective_speed(me)
    if sw == "intellect":
        return get_effective_intellect(me)
    if sw == "half_intellect":
        return _ceil_div(get_effective_intellect(me), 2)
    if sw == "opponent_predictability":
        amt = max(0, opponent.predictability)
        if reaction.cap is not None:
            amt = min(amt, reaction.cap)
        return amt
    return reaction.value


def _condition_holds(reaction, ctx) -> bool:
    c = reaction.condition
    if c is None:
        return True
    if c == "by_technique":
        return ctx.by_technique
    if c == "speed_advantage":
        return ctx.speed_advantage
    if c == "action_avoid":
        return ctx.action == "avoid"
    return True


def _consumed(me, idx, once_per) -> bool:
    st = _state(me)
    if once_per == "round":
        return idx in st["once_round"]
    if once_per == "volley":
        return idx in st["once_volley"]
    return False


def _mark_consumed(me, idx, once_per) -> None:
    st = _state(me)
    if once_per == "round":
        st["once_round"].add(idx)
    elif once_per == "volley":
        st["once_volley"].add(idx)


def _apply_effect(reaction, idx, ctx) -> None:
    me, opp = ctx.me, ctx.opponent
    eff = reaction.effect
    amount = _scaled_amount(reaction, me, opp)
    st = _state(me)

    if eff == "reduce_incoming":
        ctx.incoming_damage = max(0, ctx.incoming_damage - amount)
    elif eff == "negate_incoming":
        ctx.incoming_damage = 0
    elif eff == "bonus_outgoing":
        ctx.outgoing_damage += amount
    elif eff == "reflect":
        ctx.outgoing_damage += amount
    elif eff == "damage_reduction_lasting":
        applied = st["stacks"].get(idx, 0)
        if reaction.max_stacks is None or applied < reaction.max_stacks:
            me.damage_reduction += amount
            st["stacks"][idx] = applied + 1
    elif eff == "power_lasting":
        applied = st["stacks"].get(idx, 0)
        if reaction.max_stacks is None or applied < reaction.max_stacks:
            me.power_modifier += amount
            st["stacks"][idx] = applied + 1
    elif eff == "heal":
        me.current_health += amount
    elif eff == "cheat_death":
        me.current_health = 1
        if reaction.rider_power:
            me.power_modifier += reaction.rider_power
    elif eff == "gain_advantage":
        try:
            me.current_advantage = Advantage(reaction.advantage)
        except (ValueError, TypeError):
            pass
    elif eff == "reduce_predictability":
        me.predictability = max(0, me.predictability - amount)
    elif eff == "apply_debuff":
        try:
            db = DebuffType(reaction.debuff)
            if db not in opp.active_debuffs:
                opp.active_debuffs.append(db)
        except (ValueError, TypeError):
            pass
    elif eff == "apply_burn":
        ost = _state(opp)
        cap = reaction.max_stacks if reaction.max_stacks is not None else 99
        ost["burn_stacks"] = min(cap, ost["burn_stacks"] + max(1, amount))
    elif eff == "reposition":
        try:
            me.current_range = Range(reaction.range or "far")
        except (ValueError, TypeError):
            pass


def fire(trigger, ctx) -> bool:
    """Dispatch all of ctx.me's reactions matching `trigger`. Returns True if any applied."""
    me = ctx.me
    applied_any = False
    for idx, reaction in enumerate(me.reactions):
        if reaction.trigger != trigger.value:
            continue
        if not _condition_holds(reaction, ctx):
            continue
        if reaction.once_per and _consumed(me, idx, reaction.once_per):
            continue
        _apply_effect(reaction, idx, ctx)
        if reaction.once_per:
            _mark_consumed(me, idx, reaction.once_per)
        applied_any = True
    return applied_any
