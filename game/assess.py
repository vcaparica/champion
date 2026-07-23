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
