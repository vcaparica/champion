"""
game/ai.py - AI opponent for Champion
======================================
Provides decision-making for offline/local AI opponents.
Uses a mix of randomness and basic heuristics based on
opponent predictability and fighter stats.
"""
import random
from game.enums import ActionType, BodySlot
from game.combat import FighterInstance
from game.technique import TechniqueData


def choose_ai_actions(
    fighter: FighterInstance,
    opponent: FighterInstance,
    opponent_predictability: int = 0,
    techniques: dict[str, TechniqueData] = None
) -> list[dict]:
    """Choose 3 actions for the AI's next volley.

    A selected technique is attached automatically when the AI uses its action
    (always-on replace, mirroring the player model)."""
    if techniques is None:
        techniques = {}
    by_action = {}
    for tid in fighter.selected_techniques:
        tech = techniques.get(tid)
        if tech is not None:
            by_action[tech.base_action] = tech
    actions = []
    for _ in range(3):
        action_type = random.choice(list(ActionType))
        tech = by_action.get(action_type)
        actions.append({
            "action": action_type.value,
            "technique_id": tech.id if tech else None,
            "target_id": "opponent_0",
        })
    return actions


def choose_ai_techniques(
    fighter: FighterInstance,
    techniques: dict[str, TechniqueData]
) -> list[str]:
    """Pick base_intellect techniques from the fighter's 7-technique pool (one per action).

    Slow fighters (base_speed < 5) skip Speed-reliant techniques when enough
    alternatives remain. Auto-takes all when base_intellect >= pool size."""
    num_slots = fighter.fighter_data.base_intellect
    available = [tid for tid in fighter.fighter_data.technique_ids if tid in techniques]

    if num_slots >= len(available):
        return list(available)

    if fighter.fighter_data.base_speed < 5:
        non_speed = [tid for tid in available if tid not in SPEED_RELIANT_TECHNIQUES]
        if len(non_speed) >= num_slots:
            return random.sample(non_speed, num_slots)

    return random.sample(available, num_slots)


SPEED_RELIANT_TECHNIQUES = {
    "tempo_strike", "blitz", "momentum_edge",
    "riposte_in_a_blink", "slipstream", "predict_the_tempo",
}


def _score_item(item, base_speed):
    """Rough value of an item for a fighter of the given base Speed.

    Speed-scaling and Speed-difference effects are worth much more to a fast
    fighter and near nothing to a slow one, so a slow AI will not pick them."""
    fast = base_speed >= 5
    score = 0
    for buff in item.passive_buffs:
        if isinstance(buff, dict):
            btype = buff.get("buff_type", "")
            bval = buff.get("value", 0)
            scales = buff.get("scales_with")
            min_speed = buff.get("min_speed")
        else:
            btype = buff.buff_type.value if hasattr(buff.buff_type, "value") else str(buff.buff_type)
            bval = buff.value
            scales = buff.scales_with
            min_speed = buff.min_speed

        if min_speed is not None and base_speed < min_speed:
            continue  # inert for this fighter

        if "speed_diff" in btype:
            score += (base_speed - 3) * bval if fast else 0
            continue

        magnitude = bval
        if scales == "speed":
            magnitude = bval * base_speed
        elif scales == "speed_half":
            magnitude = bval * (base_speed // 2)
        elif scales in ("intellect", "power"):
            magnitude = bval * 4

        if "health" in btype:
            score += magnitude * 2
        elif "power" in btype:
            score += magnitude * 3
        elif "damage_reduction" in btype:
            score += magnitude
        elif "speed" in btype:
            score += magnitude
        elif "intellect" in btype:
            score += magnitude * 2
    return score


def choose_ai_items(fighter, items) -> list[str]:
    """Pick a Speed-appropriate number of items, one per slot (two for ring slots).

    Fast fighters (base_speed >= 5) trade some Speed for extra gear but keep a
    reserve; slower fighters stay lean. Never exceeds base_speed items."""
    base_speed = fighter.fighter_data.base_speed
    panoply = fighter.fighter_data.panoply

    best_per_slot = []
    for slot, item_ids in panoply.items():
        scored = [(_score_item(items[iid], base_speed), iid) for iid in item_ids if iid in items]
        if not scored:
            continue
        scored.sort(reverse=True)
        take = 2 if slot == BodySlot.RING else 1
        for score, iid in scored[:take]:
            best_per_slot.append((iid, score))

    if not best_per_slot:
        return []

    best_per_slot.sort(key=lambda x: x[1], reverse=True)

    target = base_speed - 2 if base_speed >= 5 else 2
    target = max(1, min(base_speed, target, len(best_per_slot)))
    return [iid for iid, _ in best_per_slot[:target]]


def choose_ai_fighter(fighters: dict) -> str:
    """Pick a fighter ID from the available roster."""
    if not fighters:
        return ""
    return random.choice(list(fighters.keys()))
