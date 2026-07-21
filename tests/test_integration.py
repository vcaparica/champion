"""Integration tests for Champion MVP."""
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.combat import FighterInstance, resolve_exchange, apply_buffs, compare_speed_order
from game.match import MatchState, advance_phase, check_round_end, apply_round_result
from game.enums import ActionType, MatchPhase
from game.ai import choose_ai_fighter, choose_ai_techniques, choose_ai_items, choose_ai_actions


def test_load_all_game_data():
    """All game data should load without errors."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    assert len(fighters) == 4
    assert len(techniques) == 29
    assert len(items) >= 20

    for f in fighters.values():
        assert len(f.technique_ids) == 8
        assert len(f.exclusive_technique_ids) == 2
        assert len(f.panoply) == 12  # all body slots
        assert 1 <= f.base_intellect <= 7, f"{f.id} intellect out of 1-7 range"


def test_fighter_techniques_exist():
    """All fighter technique references should resolve to actual technique files."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")

    for f in fighters.values():
        for tid in f.technique_ids:
            assert tid in techniques, f"Technique {tid} for fighter {f.id} not found"


def test_fighter_items_exist():
    """All fighter item references should resolve to actual item files."""
    fighters = load_all_fighters("game/data/fighters")
    items = load_all_items("game/data/items")

    for f in fighters.values():
        for slot, item_ids in f.panoply.items():
            for iid in item_ids:
                assert iid in items, f"Item {iid} for fighter {f.id} slot {slot} not found"


def test_complete_combat_flow():
    """Simulate a full local match from fighter select to match end."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    player_fighter = fighters["thorn"]
    ai_fighter = fighters["ember"]

    # AI picks techniques and items
    ai_instance = FighterInstance(fighter_data=ai_fighter)
    ai_techs = choose_ai_techniques(ai_instance, techniques)
    ai_items = choose_ai_items(ai_instance, items)
    ai_instance.selected_techniques = ai_techs
    ai_instance.selected_items = ai_items
    ai_instance = apply_buffs(ai_instance, items)

    # Player picks
    player_instance = FighterInstance(fighter_data=player_fighter)
    player_techs = ["iron_wall", "shield_bash", "war_cry"]
    player_items = ["iron_helm", "gauntlets_of_might"]
    player_instance.selected_techniques = player_techs
    player_instance.selected_items = player_items
    player_instance = apply_buffs(player_instance, items)

    # Verify buffs applied
    assert player_instance.current_health > player_fighter.base_health

    # Create match
    match = MatchState(team_a=[player_instance], team_b=[ai_instance])
    for _ in range(4):
        match = advance_phase(match)

    assert match.phase == MatchPhase.COMBAT

    # Simulate combat
    max_volleys = 50
    volley_count = 0
    while match.phase == MatchPhase.COMBAT and volley_count < max_volleys:
        # AI actions
        ai_actions = choose_ai_actions(ai_instance, player_instance, player_instance.predictability, techniques)
        # Player actions (random for test)
        import random
        player_actions = [
            {"action": random.choice([a.value for a in ActionType]), "technique_id": None, "target_id": "opponent"}
            for _ in range(3)
        ]

        for i in range(3):
            p_act = ActionType(player_actions[i]["action"])
            ai_act = ActionType(ai_actions[i]["action"])

            if compare_speed_order(player_instance, ai_instance) <= 0:
                result = resolve_exchange(player_instance, ai_instance, p_act, ai_act)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_attacker)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_defender)
            else:
                result = resolve_exchange(ai_instance, player_instance, ai_act, p_act)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_attacker)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_defender)

            assert result.outcome in ("hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff")

            if player_instance.current_health <= 0 or ai_instance.current_health <= 0:
                break

        winner = check_round_end(match)
        if winner:
            apply_round_result(match, winner)
            from game.match import check_match_end, reset_for_new_round
            match_winner = check_match_end(match)
            if match_winner:
                break
            if match.phase != MatchPhase.MATCH_END:
                reset_for_new_round(match)
                player_instance = match.team_a[0]
                ai_instance = match.team_b[0]

        volley_count += 1

    assert match.phase == MatchPhase.MATCH_END or match.phase == MatchPhase.ROUND_END
    assert volley_count < max_volleys, "Combat should not take more than 50 volleys"


def test_exchange_results_are_valid():
    """Every action pair should produce a valid outcome."""
    player = FighterInstance(fighter_data=load_all_fighters("game/data/fighters")["thorn"])
    ai = FighterInstance(fighter_data=load_all_fighters("game/data/fighters")["ember"])

    valid_outcomes = {"hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff"}

    for a_act in ActionType:
        for d_act in ActionType:
            result = resolve_exchange(player, ai, a_act, d_act)
            assert result.outcome in valid_outcomes, f"Invalid outcome for {a_act.value} vs {d_act.value}: {result.outcome}"
            assert result.damage_to_defender >= 0
            assert result.damage_to_attacker >= 0
            assert len(result.flavor_text) > 0
