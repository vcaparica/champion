"""
game/ai.py - AI opponent for Champion
======================================
Provides decision-making for offline/local AI opponents.
Uses a mix of randomness and basic heuristics based on
opponent predictability and fighter stats.
"""
import random
from game.enums import ActionType
from game.combat import FighterInstance
from game.technique import TechniqueData


def choose_ai_actions(
    fighter: FighterInstance,
    opponent: FighterInstance,
    opponent_predictability: int = 0,
    techniques: dict[str, TechniqueData] = None
) -> list[dict]:
    """Choose 3 actions for the AI's next volley.

    Uses opponent predictability: higher predictability means the AI
    can better guess the opponent's next action and counter it.
    """
    if techniques is None:
        techniques = {}

    actions = []
    all_action_types = list(ActionType)

    # Build available technique IDs for this match
    available_tech_ids = fighter.selected_techniques

    for i in range(3):
        action_type = random.choice(all_action_types)

        # Decide whether to use a technique
        technique_id = None
        if available_tech_ids and random.random() < 0.4:
            technique_id = random.choice(available_tech_ids)

        target_id = "opponent_0"
        actions.append({
            "action": action_type.value,
            "technique_id": technique_id,
            "target_id": target_id
        })

    return actions


def choose_ai_techniques(
    fighter: FighterInstance,
    techniques: dict[str, TechniqueData]
) -> list[str]:
    """Pick techniques from the fighter's available list.
    Number equals the fighter's base intellect."""
    num_slots = fighter.fighter_data.base_intellect
    available = [tid for tid in fighter.fighter_data.technique_ids if tid in techniques]
    if num_slots >= len(available):
        return list(available)
    if len(available) >= num_slots:
        return random.sample(available, num_slots)

    # Pad with random techniques from the full pool if needed
    result = list(available)
    all_tech_ids = list(techniques.keys())
    remaining = [tid for tid in all_tech_ids if tid not in result]
    random.shuffle(remaining)
    while len(result) < num_slots and remaining:
        result.append(remaining.pop())

    return result


def choose_ai_items(
    fighter: FighterInstance,
    items: dict
) -> list[str]:
    """Pick 2 items from the fighter's panoply.

    Strategy: prefer items with health and power buffs.
    Falls back to all available items if the fighter has no panoply entries.
    """
    all_item_ids = []
    for slot, item_ids in fighter.fighter_data.panoply.items():
        all_item_ids.extend(item_ids)

    # If panoply is empty, the AI gets no items
    if not all_item_ids:
        return []

    valid_items = [iid for iid in all_item_ids if iid in items]

    if len(valid_items) <= 2:
        return valid_items

    # Score items: power > health > damage_reduction > speed
    scored = []
    for iid in valid_items:
        item = items[iid]
        score = 0
        for buff in item.passive_buffs:
            # Handle both dict and object formats
            if isinstance(buff, dict):
                btype = buff.get("buff_type", "")
                bval = buff.get("value", 0)
            else:
                btype = buff.buff_type.value if hasattr(buff.buff_type, 'value') else str(buff.buff_type)
                bval = buff.value
            if "health" in btype:
                score += bval * 2
            elif "power" in btype:
                score += bval * 3
            elif "damage_reduction" in btype:
                score += bval
            elif "speed" in btype:
                score += bval
            elif "intellect" in btype:
                score += bval * 2
        scored.append((iid, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:2]]


def choose_ai_fighter(fighters: dict) -> str:
    """Pick a fighter ID from the available roster."""
    if not fighters:
        return ""
    return random.choice(list(fighters.keys()))
