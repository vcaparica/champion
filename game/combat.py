"""
game/combat.py - Combat engine for Champion
============================================
Core combat resolution: interaction matrix, exchange resolution,
damage calculation, buff application, and fighter instance tracking.
"""
from dataclasses import dataclass, field
from typing import Optional
from game.enums import ActionType, Range, Advantage, DebuffType, BuffType
from game.fighter import FighterData
from game.technique import TechniqueData


@dataclass
class FighterInstance:
    """Runtime state of a fighter during a match."""
    fighter_data: FighterData
    current_health: int = 0
    current_range: Range = Range.MEDIUM
    current_advantage: Advantage = Advantage.NEUTRAL
    selected_techniques: list[str] = field(default_factory=list)
    selected_items: list[str] = field(default_factory=list)
    active_debuffs: list[DebuffType] = field(default_factory=list)
    predictability: int = 0
    power_modifier: int = 0
    speed_modifier: int = 0
    damage_reduction: int = 0
    intellect_modifier: int = 0
    damage_taken_this_round: int = 0

    def __post_init__(self):
        if self.current_health == 0:
            self.current_health = self.fighter_data.base_health * 10


@dataclass
class ExchangeResult:
    """Outcome of a single action exchange between two fighters."""
    attacker_action: ActionType
    defender_action: ActionType
    outcome: str
    damage_to_defender: int = 0
    damage_to_attacker: int = 0
    range_change: Optional[Range] = None
    attacker_advantage_change: Optional[Advantage] = None
    defender_advantage_change: Optional[Advantage] = None
    debuffs_applied: list[DebuffType] = field(default_factory=list)
    flavor_text: str = ""


def item_speed_penalty(num_items: int) -> int:
    """Speed lost to carrying items: the first item is free, each additional one costs 1."""
    return max(0, num_items - 1)


def get_effective_speed(instance: FighterInstance) -> int:
    """Get speed after item load, buffs, and debuffs."""
    speed = instance.fighter_data.base_speed + instance.speed_modifier
    speed -= item_speed_penalty(len(instance.selected_items))
    if DebuffType.SLOWED in instance.active_debuffs:
        speed -= 1
    return max(1, speed)


def get_effective_power(instance: FighterInstance) -> int:
    """Get power after buffs and debuffs."""
    power = instance.fighter_data.base_power + instance.power_modifier
    if DebuffType.WEAKENED in instance.active_debuffs:
        power = max(1, power - 1)
    return max(1, power)


def get_effective_intellect(instance: FighterInstance) -> int:
    """Get intellect after buffs and debuffs."""
    intellect = instance.fighter_data.base_intellect + instance.intellect_modifier
    if DebuffType.DAZED in instance.active_debuffs:
        intellect = max(1, intellect - 1)
    return max(1, intellect)


def compare_speed_order(f1: FighterInstance, f2: FighterInstance) -> int:
    """Determine which fighter acts first in an exchange.

    Returns:
        -1 if f1 is faster (or wins intellect tie-breaker)
        1 if f2 is faster (or wins intellect tie-breaker)
        0 if true tie (equal speed and intellect)
    """
    f1_speed = get_effective_speed(f1)
    f2_speed = get_effective_speed(f2)
    if f1_speed > f2_speed:
        return -1
    if f2_speed > f1_speed:
        return 1
    # Speed tie: break by intellect
    f1_int = get_effective_intellect(f1)
    f2_int = get_effective_intellect(f2)
    if f1_int > f2_int:
        return -1
    if f2_int > f1_int:
        return 1
    return 0


def compute_damage(base_power: int, advantage: Advantage, is_vulnerable: bool = False, damage_reduction: int = 0) -> int:
    """Compute base damage from power and advantage."""
    damage = base_power
    if advantage == Advantage.OFFENSIVE:
        damage += 1
    elif advantage == Advantage.DEFENSIVE:
        damage = max(1, damage - 1)
    if is_vulnerable:
        damage += 1
    damage -= damage_reduction
    return max(1, damage)


def apply_buffs(instance: FighterInstance, all_items: dict) -> FighterInstance:
    """Apply passive buffs from selected items to a fighter instance."""
    for item_id in instance.selected_items:
        if item_id in all_items:
            item = all_items[item_id]
            for buff in item.passive_buffs:
                # Handle both dict and ItemBuff formats
                if isinstance(buff, dict):
                    buff_type = BuffType(buff["buff_type"])
                    value = buff["value"]
                    scales_with = buff.get("scales_with")
                else:
                    buff_type = buff.buff_type
                    value = buff.value
                    scales_with = buff.scales_with

                # Apply scaling if the buff scales with an attribute
                if scales_with == "intellect":
                    value = value * get_effective_intellect(instance)
                elif scales_with == "power":
                    value = value * get_effective_power(instance)
                elif scales_with == "speed":
                    value = value * get_effective_speed(instance)
                if buff_type == BuffType.HEALTH:
                    instance.current_health += value
                elif buff_type == BuffType.POWER:
                    instance.power_modifier += value
                elif buff_type == BuffType.SPEED:
                    instance.speed_modifier += value
                elif buff_type == BuffType.INTELLECT:
                    instance.intellect_modifier += value
                elif buff_type == BuffType.DAMAGE_REDUCTION:
                    instance.damage_reduction += value
                elif buff_type == BuffType.RESIST_DEBUFF:
                    pass  # Handled during debuff application
    return instance


def resolve_exchange(
    attacker: FighterInstance,
    defender: FighterInstance,
    attacker_action: ActionType,
    defender_action: ActionType,
    attacker_technique: Optional[TechniqueData] = None,
    defender_technique: Optional[TechniqueData] = None
) -> ExchangeResult:
    """Resolve a single action exchange between two fighters."""
    result = ExchangeResult(
        attacker_action=attacker_action,
        defender_action=defender_action,
        outcome="hit"
    )

    a_power = get_effective_power(attacker)
    d_power = get_effective_power(defender)
    a_speed = get_effective_speed(attacker)
    d_speed = get_effective_speed(defender)

    # intellect_to_speed override: replace speed with intellect for this exchange
    if attacker_technique and attacker_technique.effects.intellect_to_speed:
        a_speed = get_effective_intellect(attacker)
    if defender_technique and defender_technique.effects.intellect_to_speed:
        d_speed = get_effective_intellect(defender)

    a_vulnerable = DebuffType.VULNERABLE in attacker.active_debuffs
    d_vulnerable = DebuffType.VULNERABLE in defender.active_debuffs

    a_damage = compute_damage(a_power, attacker.current_advantage, d_vulnerable, defender.damage_reduction)
    d_damage = compute_damage(d_power, defender.current_advantage, a_vulnerable, attacker.damage_reduction)

    # Apply technique damage modifier
    if attacker_technique:
        a_damage += attacker_technique.effects.damage_modifier
        attacker.predictability += attacker_technique.predictability_increase
        if attacker_technique.effects.gain_advantage:
            try:
                result.attacker_advantage_change = Advantage(attacker_technique.effects.gain_advantage)
            except ValueError:
                pass
        if attacker_technique.effects.apply_debuff:
            try:
                result.debuffs_applied.append(DebuffType(attacker_technique.effects.apply_debuff))
            except ValueError:
                pass
        if attacker_technique.effects.reposition_to:
            try:
                result.range_change = Range(attacker_technique.effects.reposition_to)
            except ValueError:
                pass
        if attacker_technique.effects.heal_on_hit:
            # Healing applied after interaction matrix determines outcome
            pass

    if defender_technique:
        d_damage += defender_technique.effects.damage_modifier
        defender.predictability += defender_technique.predictability_increase
        if defender_technique.effects.gain_advantage:
            try:
                result.defender_advantage_change = Advantage(defender_technique.effects.gain_advantage)
            except ValueError:
                pass

    # Apply intellect-scaling damage for attacker
    if attacker_technique:
        if attacker_technique.effects.intellect_damage_scale:
            a_damage += get_effective_intellect(attacker) * attacker_technique.effects.intellect_damage_scale
        if attacker_technique.effects.opponent_intellect_scale:
            a_damage += max(0, 7 - get_effective_intellect(defender)) * attacker_technique.effects.opponent_intellect_scale
        if attacker_technique.effects.require_intellect_advantage:
            if get_effective_intellect(attacker) < get_effective_intellect(defender):
                a_damage -= attacker_technique.effects.damage_modifier

    # Apply intellect-based damage reduction for defender
    if defender_technique and defender_technique.effects.intellect_damage_reduction:
        # Ceil division: -(-(n) // d) rounds n/d up
        dr_amount = -(-(get_effective_intellect(defender) * defender_technique.effects.intellect_damage_reduction) // 2)
        a_damage = max(1, a_damage - dr_amount)

    # Interaction matrix
    pair = (attacker_action, defender_action)

    if pair == (ActionType.STRIKE, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The strike lands true as the feint is exposed!"

    elif pair == (ActionType.STRIKE, ActionType.BLOCK):
        result.outcome = "blocked"
        result.flavor_text = "The strike is stopped cold by a solid block."

    elif pair == (ActionType.STRIKE, ActionType.COUNTER):
        result.outcome = "countered"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The strike is turned aside and the counter lands!"

    elif pair == (ActionType.STRIKE, ActionType.AVOID):
        result.outcome = "miss"
        result.flavor_text = "The strike hits only air as the opponent dodges away."

    elif pair == (ActionType.STRIKE, ActionType.CHARGE):
        result.outcome = "hit"
        order = compare_speed_order(attacker, defender)
        if order == 1:  # defender faster — interrupts charge
            result.damage_to_attacker = a_damage
            result.damage_to_defender = 0
            result.flavor_text = "The strike lands first, stopping the charge in its tracks!"
        else:
            result.damage_to_defender = d_damage
            result.damage_to_attacker = a_damage
            result.flavor_text = "The charge crashes through the strike, both combatants feel the impact!"

    elif pair == (ActionType.STRIKE, ActionType.STRIKE):
        result.outcome = "clash"
        order = compare_speed_order(attacker, defender)
        if order == -1:  # attacker faster
            result.damage_to_defender = a_damage
            result.damage_to_attacker = max(1, d_damage // 2)
        elif order == 1:  # defender faster
            result.damage_to_attacker = d_damage
            result.damage_to_defender = max(1, a_damage // 2)
        else:  # true tie
            result.damage_to_defender = max(1, a_damage // 2)
            result.damage_to_attacker = max(1, d_damage // 2)
        result.flavor_text = "Steel meets steel in a shower of sparks!"

    elif pair == (ActionType.BLOCK, ActionType.STRIKE):
        result.outcome = "blocked"
        result.flavor_text = "The incoming strike is turned away by a firm block."

    elif pair == (ActionType.BLOCK, ActionType.BLOCK):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters brace behind their guards. Nothing happens."

    elif pair == (ActionType.BLOCK, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The block is useless against the feint! The defender strikes through."

    elif pair == (ActionType.BLOCK, ActionType.COUNTER):
        result.outcome = "blocked"
        result.flavor_text = "The counter finds only solid defense."

    elif pair == (ActionType.BLOCK, ActionType.CHARGE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The charge shatters through the block!"

    elif pair == (ActionType.BLOCK, ActionType.AVOID):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters reposition cautiously."

    elif pair == (ActionType.FEINT, ActionType.STRIKE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The feint is seen through! A strike punishes the deception."

    elif pair == (ActionType.FEINT, ActionType.BLOCK):
        result.outcome = "bypassed"
        result.damage_to_defender = a_damage
        result.flavor_text = "The feint slips past the block effortlessly!"

    elif pair == (ActionType.FEINT, ActionType.FEINT):
        result.outcome = "clash"
        result.flavor_text = "Both fighters try to deceive each other. Neither lands cleanly."

    elif pair == (ActionType.FEINT, ActionType.COUNTER):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The feint tricks the counter, creating an opening!"

    elif pair == (ActionType.FEINT, ActionType.CHARGE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The feint is meaningless against the unstoppable charge!"

    elif pair == (ActionType.FEINT, ActionType.AVOID):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The feint reads the dodge perfectly and strikes where the opponent moves!"

    elif pair == (ActionType.COUNTER, ActionType.STRIKE):
        result.outcome = "countered"
        result.damage_to_defender = a_damage
        result.flavor_text = "The counter catches the strike and punishes it!"

    elif pair == (ActionType.COUNTER, ActionType.BLOCK):
        result.outcome = "blocked"
        result.flavor_text = "The counter is anticipated and blocked."

    elif pair == (ActionType.COUNTER, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The counter is fooled by the feint and leaves an opening!"

    elif pair == (ActionType.COUNTER, ActionType.COUNTER):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters wait for the other to commit. Nothing happens."

    elif pair == (ActionType.COUNTER, ActionType.CHARGE):
        result.outcome = "countered"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge is telegraphed and the counter lands perfectly!"

    elif pair == (ActionType.COUNTER, ActionType.AVOID):
        result.outcome = "whiff"
        result.flavor_text = "The counter finds nothing as the opponent slips away."

    elif pair == (ActionType.CHARGE, ActionType.STRIKE):
        result.outcome = "hit"
        order = compare_speed_order(attacker, defender)
        if order == -1:  # attacker faster — charge hits first
            result.damage_to_defender = a_damage
            result.damage_to_attacker = 0
            result.flavor_text = "The charge hits first, overwhelming the strike!"
        else:
            result.damage_to_attacker = d_damage
            result.flavor_text = "The strike catches the charger before they build momentum!"

    elif pair == (ActionType.CHARGE, ActionType.BLOCK):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge breaks through the block with devastating force!"

    elif pair == (ActionType.CHARGE, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge barrels through the feint!"

    elif pair == (ActionType.CHARGE, ActionType.COUNTER):
        result.outcome = "countered"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The counter catches the charging opponent!"

    elif pair == (ActionType.CHARGE, ActionType.CHARGE):
        result.outcome = "clash"
        result.damage_to_defender = a_damage + 1
        result.damage_to_attacker = d_damage + 1
        result.flavor_text = "Both fighters charge! The collision is devastating!"

    elif pair == (ActionType.CHARGE, ActionType.AVOID):
        result.outcome = "miss"
        result.flavor_text = "The charge thunders past as the opponent sidesteps."

    elif pair == (ActionType.AVOID, ActionType.STRIKE):
        result.outcome = "miss"
        result.flavor_text = "The dodge evades the strike completely."

    elif pair == (ActionType.AVOID, ActionType.BLOCK):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters stay defensive."

    elif pair == (ActionType.AVOID, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The dodge is read and punished by the feint!"

    elif pair == (ActionType.AVOID, ActionType.COUNTER):
        result.outcome = "whiff"
        result.flavor_text = "Neither fighter commits. A moment of stillness."

    elif pair == (ActionType.AVOID, ActionType.CHARGE):
        result.outcome = "miss"
        result.flavor_text = "The dodge avoids the charge completely!"

    elif pair == (ActionType.AVOID, ActionType.AVOID):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters reposition, circling each other."
        result.range_change = Range.FAR

    else:
        result.outcome = "whiff"
        result.flavor_text = "The actions cancel each other out."

    # Apply technique healing
    if attacker_technique and attacker_technique.effects.heal_on_hit and result.outcome == "hit":
        attacker.current_health += attacker_technique.effects.heal_on_hit
        result.flavor_text += f" {attacker.fighter_data.name} recovers stamina."

    # Ensure non-negative damage
    result.damage_to_defender = max(0, result.damage_to_defender)
    result.damage_to_attacker = max(0, result.damage_to_attacker)

    return result
