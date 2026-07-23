"""
game/reactions.py - Reactive engine for Champion
=================================================
A small trigger/condition/effect system. Feats and (via an adapter) item
reactives contribute Reaction rules to a FighterInstance's `reactions` list;
`fire()` dispatches them at combat hook points, mutating instances and the
per-hit damage carried on a ReactionContext.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from game.enums import Advantage, DebuffType, Range, ActionType
from game.combat import get_effective_speed, get_effective_intellect
from game.feat import Reaction


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
    notes: list = field(default_factory=list)


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


def _note(ctx, text: str) -> None:
    """Append a narration note to the current exchange context (if it has one)."""
    ctx.notes.append(text)


def _apply_effect(reaction, idx, ctx) -> None:
    me, opp = ctx.me, ctx.opponent
    eff = reaction.effect
    amount = _scaled_amount(reaction, me, opp)
    st = _state(me)

    if eff == "reduce_incoming":
        ctx.incoming_damage = max(0, ctx.incoming_damage - amount)
    elif eff == "negate_incoming":
        ctx.incoming_damage = 0
        _note(ctx, f"{me.fighter_data.name} is untouched!")
    elif eff == "bonus_outgoing":
        ctx.outgoing_damage += amount
    elif eff == "reflect":
        ctx.outgoing_damage += amount
        _note(ctx, f"{me.fighter_data.name} strikes back for {amount}!")
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
        _note(ctx, f"{me.fighter_data.name} recovers {amount} HP.")
    elif eff == "cheat_death":
        me.current_health = 1
        if reaction.rider_power:
            me.power_modifier += reaction.rider_power
        _note(ctx, f"{me.fighter_data.name} refuses to fall, holding on at 1 HP!")
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
        _note(ctx, f"{opp.fighter_data.name} catches fire.")
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


_ITEM_TRIGGER_MAP = {
    "when_struck": ("take_damage", None),
    "when_hit_by_technique": ("take_damage", "by_technique"),
    "when_avoid_success": ("defense_success", "action_avoid"),
    "when_low_health": ("low_health", None),
}

_ITEM_EFFECT_MAP = {
    "heal": "heal",
    "power_boost": "power_lasting",
    "damage_reduction": "reduce_incoming",
    "counter_damage": "reflect",
    "gain_advantage": "gain_advantage",
    "reposition": "reposition",
}


def _adapt_item_reactive(reactive):
    """Map an ItemReactive onto a Reaction, or None if the trigger/effect is unknown."""
    tmap = _ITEM_TRIGGER_MAP.get(reactive.trigger)
    emap = _ITEM_EFFECT_MAP.get(reactive.effect)
    if tmap is None or emap is None:
        return None
    trigger, condition = tmap
    reaction = Reaction(trigger=trigger, effect=emap, value=reactive.value, condition=condition)
    if emap == "gain_advantage":
        reaction.advantage = "offensive"
    if emap == "reposition":
        reaction.range = "far"
    return reaction


def attach_reactions(instance, feats, items):
    """Populate instance.feat and instance.reactions from the fighter's Feat and item reactives."""
    reactions = []
    feat = None
    fid = getattr(instance.fighter_data, "feat_id", "")
    if fid and fid in feats:
        feat = feats[fid]
        reactions.extend(feat.reactions)
    for item_id in instance.selected_items:
        item = items.get(item_id)
        if item is not None and getattr(item, "reactive", None):
            adapted = _adapt_item_reactive(item.reactive)
            if adapted is not None:
                reactions.append(adapted)
    instance.feat = feat
    instance.reactions = reactions
    return instance


def tick_burn(instance) -> int:
    """Apply burn damage (bypassing damage reduction) at exchange start.

    Returns the actual health lost (clamped at the fighter's remaining health),
    so the spoken "takes N burn damage" line is accurate."""
    st = _state(instance)
    stacks = st.get("burn_stacks", 0)
    if stacks <= 0:
        return 0
    lost = min(stacks, instance.current_health)
    instance.current_health = max(0, instance.current_health - lost)
    return lost


def commit_damage(me, opponent, amount) -> int:
    """Apply `amount` damage to `me`, honoring a once-per-round cheat-death.

    Returns (new_health, cheated). `cheated` is True when a WOULD_FALL reaction
    fired (cheat-death), so the caller can announce the near-death save."""
    if amount > 0 and amount >= me.current_health:
        ctx = ReactionContext(me=me, opponent=opponent)
        if fire(Trigger.WOULD_FALL, ctx):
            return me.current_health, True
    me.current_health = max(0, me.current_health - amount)
    return me.current_health, False


def fire_low_health(instance, opponent, threshold_ratio: float = 0.25) -> None:
    """Fire LOW_HEALTH reactions once per round when at/below the threshold."""
    st = _state(instance)
    if st.get("low_health_fired"):
        return
    max_hp = instance.round_start_health or instance.fighter_data.base_health * 10
    if 0 < instance.current_health <= max_hp * threshold_ratio:
        ctx = ReactionContext(me=instance, opponent=opponent)
        if fire(Trigger.LOW_HEALTH, ctx):
            st["low_health_fired"] = True


def clear_volley_state(instance) -> None:
    """Reset per-volley once gates at the start of a volley."""
    _state(instance)["once_volley"] = set()


# Matrix cells where an offensive action (strike/charge/feint) is fully stopped by a
# defensive action (block/avoid). Keyed by (attacker_action, defender_action).
_DEFENSE_SUCCESS_DEFENDER = {
    (ActionType.STRIKE, ActionType.BLOCK),
    (ActionType.STRIKE, ActionType.AVOID),
    (ActionType.CHARGE, ActionType.AVOID),
}
_DEFENSE_SUCCESS_ATTACKER = {
    (ActionType.BLOCK, ActionType.STRIKE),
    (ActionType.AVOID, ActionType.STRIKE),
    (ActionType.AVOID, ActionType.CHARGE),
}


def _fire_deal_take(dealer, receiver, damage, by_technique):
    """Fire DEAL_DAMAGE on dealer then TAKE_DAMAGE on receiver for one damage figure.

    Returns (final_damage, notes)."""
    deal_ctx = ReactionContext(
        me=dealer, opponent=receiver, outgoing_damage=damage,
        speed_advantage=(get_effective_speed(dealer) >= get_effective_speed(receiver)),
    )
    fire(Trigger.DEAL_DAMAGE, deal_ctx)
    take_ctx = ReactionContext(
        me=receiver, opponent=dealer, incoming_damage=deal_ctx.outgoing_damage,
        by_technique=by_technique,
    )
    fire(Trigger.TAKE_DAMAGE, take_ctx)
    return max(0, take_ctx.incoming_damage), deal_ctx.notes + take_ctx.notes


def apply_exchange_reactions(attacker, defender, result, a_tech=None, d_tech=None) -> None:
    """Run the reaction phase over an already-resolved exchange, mutating result and instances."""
    notes = []
    if result.damage_to_defender > 0:
        result.damage_to_defender, n = _fire_deal_take(
            attacker, defender, result.damage_to_defender, a_tech is not None)
        notes.extend(n)
    if result.damage_to_attacker > 0:
        result.damage_to_attacker, n = _fire_deal_take(
            defender, attacker, result.damage_to_attacker, d_tech is not None)
        notes.extend(n)

    # These cells are always zero-damage to the defender in the interaction matrix
    # (a pure negation), which is what makes keying on the action pair safe.
    pair = (result.attacker_action, result.defender_action)
    if pair in _DEFENSE_SUCCESS_DEFENDER:
        ctx = ReactionContext(me=defender, opponent=attacker, action=result.defender_action.value)
        fire(Trigger.DEFENSE_SUCCESS, ctx)
        result.damage_to_attacker += ctx.outgoing_damage
        notes.extend(ctx.notes)
    elif pair in _DEFENSE_SUCCESS_ATTACKER:
        ctx = ReactionContext(me=attacker, opponent=defender, action=result.attacker_action.value)
        fire(Trigger.DEFENSE_SUCCESS, ctx)
        result.damage_to_defender += ctx.outgoing_damage
        notes.extend(ctx.notes)

    if notes:
        result.flavor_text += " " + " ".join(notes)
