"""
game/assess.py - Assess action reveal and technique-effect engine.
===================================================================
Owns the two-tier information reveal of the plain Assess action and the
special effects of Assess techniques. Per-opponent reveal progress lives
in the assessor's dedicated assess_state field (match-long); transient
pending buffs live in reaction_state['assess_buffs'] (cleared each round).
"""
from game.enums import ActionType
from game.combat import get_effective_speed, get_effective_power, get_effective_intellect


def _opp_state(me, opponent) -> dict:
    """Per-opponent reveal progress (match-long)."""
    key = opponent.fighter_data.id
    return me.assess_state.setdefault(
        key, {"attributes_revealed": False, "successes_this_round": 0}
    )


def _attributes_text(opponent) -> str:
    return (
        f"{opponent.fighter_data.name}: Health {opponent.current_health}"
        f"/{opponent.round_start_health}, "
        f"Speed {get_effective_speed(opponent)}, "
        f"Power {get_effective_power(opponent)}, "
        f"Intellect {get_effective_intellect(opponent)}."
    )


def _opponent_technique_actions(opponent, techniques) -> list:
    actions = []
    for tid in opponent.selected_techniques:
        tech = techniques.get(tid) if techniques else None
        if tech is not None:
            actions.append(tech.base_action.value.capitalize())
    return actions


def _techniques_text(opponent, techniques) -> str:
    actions = _opponent_technique_actions(opponent, techniques)
    if actions:
        joined = ", ".join(sorted(actions))
        return f"{opponent.fighter_data.name}'s techniques replace: {joined}."
    return f"{opponent.fighter_data.name} has no techniques in play."


def advance_assess(assessor, opponent, result, side: str, techniques: dict) -> None:
    """Advance the two-tier reveal for one successful Assess; append to result.assess_reveals."""
    st = _opp_state(assessor, opponent)
    st["successes_this_round"] += 1
    if not st["attributes_revealed"]:
        st["attributes_revealed"] = True
        st["last_kind"] = "attributes"
        result.assess_reveals.append(
            {"target": side, "kind": "attributes", "text": _attributes_text(opponent)}
        )
    elif st["successes_this_round"] == 2:
        st["last_kind"] = "techniques"
        result.assess_reveals.append(
            {"target": side, "kind": "techniques", "text": _techniques_text(opponent, techniques)}
        )
    else:
        # Re-state the most recent reveal. Each exchange carries its own fresh
        # ExchangeResult, so the last kind is read from the match-long assessor
        # state, not the transient result.assess_reveals.
        kind = st.get("last_kind", "attributes")
        text = (_attributes_text(opponent) if kind == "attributes"
                else _techniques_text(opponent, techniques))
        result.assess_reveals.append({"target": side, "kind": kind, "text": text})


def format_reveals_for(reveals: list, side: str) -> list:
    """Return the reveal speech texts addressed to `side` ('attacker' or 'defender')."""
    return [r["text"] for r in reveals if r.get("target") == side]


def process_assess_exchange(attacker, defender, result, a_tech=None, d_tech=None,
                            techniques=None, items=None) -> None:
    """Run Assess processing for one exchange: consume pending buffs, then reveals/effects."""
    consume_pending_buffs(attacker, defender, result)
    if result.outcome == "assessed":
        if result.attacker_action == ActionType.ASSESS:
            advance_assess(attacker, defender, result, "attacker", techniques)
            apply_assess_technique(attacker, defender, result, "attacker", a_tech, techniques, items)
        if result.defender_action == ActionType.ASSESS:
            advance_assess(defender, attacker, result, "defender", techniques)
            apply_assess_technique(defender, attacker, result, "defender", d_tech, techniques, items)


def _buffs(me) -> dict:
    return me.reaction_state.setdefault("assess_buffs", {})


def set_pending_counter_bonus(me, amount: int) -> None:
    """A found weak spot: bonus added to the next successful counter that lands."""
    b = _buffs(me)
    b["counter_bonus"] = max(amount, b.get("counter_bonus", 0))


def set_pending_damage_half(me) -> None:
    """Roll with the hit: halve the next damage taken, once."""
    _buffs(me)["damage_half"] = True


def apply_speed_buff(me, amount: int, volleys: int) -> None:
    """Predict the opponent: +Speed for `volleys` volleys (non-stacking)."""
    b = _buffs(me)
    prev = b.get("speed_buff")
    if prev:
        me.speed_modifier -= prev["amount"]
    b["speed_buff"] = {"amount": amount, "volleys": max(1, volleys)}
    me.speed_modifier += amount


def tick_speed_buff(me) -> None:
    """Count down the speed buff one volley; remove it when expired."""
    b = _buffs(me)
    sb = b.get("speed_buff")
    if not sb:
        return
    sb["volleys"] -= 1
    if sb["volleys"] <= 0:
        me.speed_modifier -= sb["amount"]
        del b["speed_buff"]


def _reveal_unused_technique(assessor, opponent, result, side, techniques) -> None:
    if not techniques:
        return
    candidates = [tid for tid in opponent.selected_techniques
                  if tid not in opponent.techniques_used]
    if not candidates:
        return
    tech = techniques.get(candidates[0])
    if tech is None:
        return
    text = f"{opponent.fighter_data.name} holds in reserve: {tech.name} - {tech.description}."
    result.assess_reveals.append({"target": side, "kind": "unused_technique", "text": text})


def _reveal_item(assessor, opponent, result, side, items) -> None:
    if not items:
        return
    st = _opp_state(assessor, opponent)
    revealed = st.setdefault("items_revealed", set())
    candidates = [iid for iid in opponent.selected_items if iid not in revealed]
    if not candidates:
        return
    item = items.get(candidates[0])
    if item is None:
        return
    revealed.add(candidates[0])
    text = f"{opponent.fighter_data.name} bears: {item.name} - {item.description}."
    result.assess_reveals.append({"target": side, "kind": "item", "text": text})


def apply_assess_technique(assessor, opponent, result, side, technique,
                           techniques, items) -> None:
    """Apply an Assess technique's special effects on a successful Assess."""
    if technique is None:
        return
    eff = technique.effects
    if eff.assess_next_counter_bonus:
        set_pending_counter_bonus(assessor, eff.assess_next_counter_bonus)
    if eff.assess_next_damage_half:
        set_pending_damage_half(assessor)
    if eff.assess_speed_buff:
        apply_speed_buff(assessor, eff.assess_speed_buff, eff.assess_speed_buff_volleys or 3)
    if eff.assess_reveal_unused_technique:
        _reveal_unused_technique(assessor, opponent, result, side, techniques)
    if eff.assess_reveal_item:
        _reveal_item(assessor, opponent, result, side, items)


# Task 8 placeholder: real buff-consumption logic (counter bonus, damage
# halving) lands in Task 8. This stub exists only so Task 7's tests pass.
def consume_pending_buffs(attacker, defender, result):
    return
