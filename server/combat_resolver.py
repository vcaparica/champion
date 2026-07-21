"""
server/combat_resolver.py - Server-side combat resolution
===========================================================
Authoritatively resolves combat exchanges on the server.
"""
from game.combat import resolve_exchange, FighterInstance, get_effective_speed, compare_speed_order
from game.enums import ActionType


def resolve_volley_server(match) -> dict:
    """Resolve a full volley (3 exchanges) for a match.

    Returns a volley_result message dict with all exchange outcomes.
    """
    state = match.match_state
    attacker = state.team_a[0]
    defender = state.team_b[0]

    a_actions = state.actions_declared_a
    b_actions = state.actions_declared_b

    exchanges = []
    for i in range(3):
        a_act = a_actions[i] if i < len(a_actions) else {"action": "strike", "technique_id": None, "target_id": "opponent"}
        b_act = b_actions[i] if i < len(b_actions) else {"action": "strike", "technique_id": None, "target_id": "opponent"}

        try:
            a_action_type = ActionType(a_act["action"])
        except ValueError:
            a_action_type = ActionType.STRIKE
        try:
            b_action_type = ActionType(b_act["action"])
        except ValueError:
            b_action_type = ActionType.STRIKE

        # Determine who is attacker/defender for this exchange
        # In 1v1, the faster fighter attacks first (ties resolved by intellect)
        # TODO: Load technique data on the server and pass real TechniqueData objects.
        # For now, techniques are passed as None, making technique effects inert server-side.
        a_technique = None
        b_technique = None

        order = compare_speed_order(attacker, defender)
        if order <= 0:  # attacker goes first
            result = resolve_exchange(
                attacker, defender, a_action_type, b_action_type,
                attacker_technique=a_technique, defender_technique=b_technique
            )
            exchange = {
                "exchange_num": i + 1,
                "attacker_name": attacker.fighter_data.name,
                "defender_name": defender.fighter_data.name,
                "attacker_action": result.attacker_action.value,
                "defender_action": result.defender_action.value,
                "outcome": result.outcome,
                "damage_to_defender": result.damage_to_defender,
                "damage_to_attacker": result.damage_to_attacker,
                "flavor_text": result.flavor_text,
                "attacker_health": max(0, attacker.current_health - result.damage_to_attacker),
                "defender_health": max(0, defender.current_health - result.damage_to_defender),
            }
            # Apply damage
            defender.current_health = max(0, defender.current_health - result.damage_to_defender)
            attacker.current_health = max(0, attacker.current_health - result.damage_to_attacker)
            attacker.damage_taken_this_round += result.damage_to_attacker
            defender.damage_taken_this_round += result.damage_to_defender

            # Apply range and advantage changes
            if result.range_change:
                attacker.current_range = result.range_change
            if result.attacker_advantage_change:
                attacker.current_advantage = result.attacker_advantage_change
            if result.defender_advantage_change:
                defender.current_advantage = result.defender_advantage_change
            for debuff in result.debuffs_applied:
                if debuff not in defender.active_debuffs:
                    defender.active_debuffs.append(debuff)
        else:
            result = resolve_exchange(
                defender, attacker, b_action_type, a_action_type,
                attacker_technique=b_technique, defender_technique=a_technique
            )
            exchange = {
                "exchange_num": i + 1,
                "attacker_name": defender.fighter_data.name,
                "defender_name": attacker.fighter_data.name,
                "attacker_action": result.attacker_action.value,
                "defender_action": result.defender_action.value,
                "outcome": result.outcome,
                "damage_to_defender": result.damage_to_defender,
                "damage_to_attacker": result.damage_to_attacker,
                "flavor_text": result.flavor_text,
                "attacker_health": max(0, defender.current_health - result.damage_to_attacker),
                "defender_health": max(0, attacker.current_health - result.damage_to_defender),
            }
            attacker.current_health = max(0, attacker.current_health - result.damage_to_defender)
            defender.current_health = max(0, defender.current_health - result.damage_to_attacker)
            attacker.damage_taken_this_round += result.damage_to_defender
            defender.damage_taken_this_round += result.damage_to_attacker
            if result.range_change:
                defender.current_range = result.range_change
            if result.attacker_advantage_change:
                defender.current_advantage = result.attacker_advantage_change
            if result.defender_advantage_change:
                attacker.current_advantage = result.defender_advantage_change
            for debuff in result.debuffs_applied:
                if debuff not in attacker.active_debuffs:
                    attacker.active_debuffs.append(debuff)

        exchanges.append(exchange)

        # Check for round end mid-volley
        if attacker.current_health <= 0 or defender.current_health <= 0:
            break

    return {
        "type": "volley_result",
        "exchanges": exchanges,
    }
