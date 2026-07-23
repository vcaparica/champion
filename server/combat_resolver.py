"""
server/combat_resolver.py - Server-side combat resolution
===========================================================
Authoritatively resolves combat exchanges on the server, with full parity to
local play: real techniques, passive item buffs, Feats, item reactives, burn
ticks, cheat-death, and low-health reactions.
"""
from game.combat import resolve_exchange, compare_speed_order
from game.enums import ActionType
from game.reactions import tick_burn, commit_damage, fire_low_health, clear_volley_state

_DEFAULT_ACTION = {"action": "strike", "technique_id": None, "target_id": "opponent"}


def _action_type(declared: dict) -> ActionType:
    try:
        return ActionType(declared["action"])
    except (ValueError, KeyError):
        return ActionType.STRIKE


def _technique_for(declared: dict, instance, techniques: dict):
    """Resolve a declared technique, but only if the fighter actually selected it."""
    tid = declared.get("technique_id")
    if tid and tid in instance.selected_techniques:
        return techniques.get(tid)
    return None


def resolve_volley_server(match, techniques: dict) -> dict:
    """Resolve a full volley (3 exchanges) for a match.

    Returns a volley_result message dict with all exchange outcomes.
    """
    state = match.match_state
    fighter_a = state.team_a[0]
    fighter_b = state.team_b[0]

    # New volley: reset per-volley once-gates for both fighters
    clear_volley_state(fighter_a)
    clear_volley_state(fighter_b)

    a_actions = state.actions_declared_a
    b_actions = state.actions_declared_b

    exchanges = []
    for i in range(3):
        # Burn ticks at the start of the exchange (bypass damage reduction;
        # routed through commit_damage, so cheat-death and low-health apply).
        burn_ticks = []
        cheat_deaths = []
        for burning, other in ((fighter_a, fighter_b), (fighter_b, fighter_a)):
            lost, cheated = tick_burn(burning, other)
            if lost:
                burn_ticks.append([burning.fighter_data.name, lost])
            if cheated:
                cheat_deaths.append(burning.fighter_data.name)
        fire_low_health(fighter_a, fighter_b)
        fire_low_health(fighter_b, fighter_a)

        if fighter_a.current_health <= 0 or fighter_b.current_health <= 0:
            break

        a_act = a_actions[i] if i < len(a_actions) else _DEFAULT_ACTION
        b_act = b_actions[i] if i < len(b_actions) else _DEFAULT_ACTION
        a_action_type = _action_type(a_act)
        b_action_type = _action_type(b_act)
        a_technique = _technique_for(a_act, fighter_a, techniques)
        b_technique = _technique_for(b_act, fighter_b, techniques)

        # In 1v1, the faster fighter attacks first (ties resolved by intellect).
        order = compare_speed_order(fighter_a, fighter_b)
        if order <= 0:
            attacker, defender = fighter_a, fighter_b
            result = resolve_exchange(
                attacker, defender, a_action_type, b_action_type,
                attacker_technique=a_technique, defender_technique=b_technique
            )
        else:
            attacker, defender = fighter_b, fighter_a
            result = resolve_exchange(
                attacker, defender, b_action_type, a_action_type,
                attacker_technique=b_technique, defender_technique=a_technique
            )

        _, attacker_cheated = commit_damage(attacker, defender, result.damage_to_attacker)
        _, defender_cheated = commit_damage(defender, attacker, result.damage_to_defender)
        if attacker_cheated:
            cheat_deaths.append(attacker.fighter_data.name)
        if defender_cheated:
            cheat_deaths.append(defender.fighter_data.name)
        attacker.damage_taken_this_round += result.damage_to_attacker
        defender.damage_taken_this_round += result.damage_to_defender
        fire_low_health(attacker, defender)
        fire_low_health(defender, attacker)

        if result.range_change:
            attacker.current_range = result.range_change
        if result.attacker_advantage_change:
            attacker.current_advantage = result.attacker_advantage_change
        if result.defender_advantage_change:
            defender.current_advantage = result.defender_advantage_change
        for debuff in result.debuffs_applied:
            if debuff not in defender.active_debuffs:
                defender.active_debuffs.append(debuff)

        exchanges.append({
            "exchange_num": i + 1,
            "attacker_name": attacker.fighter_data.name,
            "defender_name": defender.fighter_data.name,
            "attacker_action": result.attacker_action.value,
            "defender_action": result.defender_action.value,
            "outcome": result.outcome,
            "damage_to_defender": result.damage_to_defender,
            "damage_to_attacker": result.damage_to_attacker,
            "flavor_text": result.flavor_text,
            "attacker_health": attacker.current_health,
            "defender_health": defender.current_health,
            "burn_ticks": burn_ticks,
            "cheat_deaths": cheat_deaths,
            "reflected_damage": result.reflected_damage,
            "healed_amount": result.healed_amount,
            "burn_applied": result.burn_applied,
            "reaction_debuffs": [d.value for d in result.reaction_debuffs],
        })

        # Check for round end mid-volley
        if attacker.current_health <= 0 or defender.current_health <= 0:
            break

    return {
        "type": "volley_result",
        "exchanges": exchanges,
    }
