"""Integration tests for Champion MVP."""
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.combat import FighterInstance, resolve_exchange, apply_buffs, compare_speed_order, get_effective_intellect
from game.match import MatchState, advance_phase, check_round_end, apply_round_result, clear_actions
from game.enums import ActionType, MatchPhase
from game.ai import choose_ai_fighter, choose_ai_techniques, choose_ai_items, choose_ai_actions


def test_load_all_game_data():
    """All game data should load without errors."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    assert len(fighters) == 12
    assert len(techniques) == 53  # 41 existing + 12 exclusive techniques
    assert len(items) >= 41

    for f in fighters.values():
        assert len(f.technique_ids) == 7
        assert len(f.exclusive_technique_ids) == 1
        assert sum(len(ids) for ids in f.panoply.values()) == 7
        assert 2 <= f.base_intellect <= 6, f"{f.id} intellect out of range"


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

    player_fighter = fighters["anvil"]
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
    player_techs = ["iron_wall", "giants_swing", "juggernaut_blow"]
    player_items = ["iron_helm", "ring_of_vitality"]
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

            assert result.outcome in ("hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff", "assessed")

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
    player = FighterInstance(fighter_data=load_all_fighters("game/data/fighters")["anvil"])
    ai = FighterInstance(fighter_data=load_all_fighters("game/data/fighters")["ember"])

    valid_outcomes = {"hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff", "assessed"}

    for a_act in ActionType:
        for d_act in ActionType:
            result = resolve_exchange(player, ai, a_act, d_act)
            assert result.outcome in valid_outcomes, f"Invalid outcome for {a_act.value} vs {d_act.value}: {result.outcome}"
            assert result.damage_to_defender >= 0
            assert result.damage_to_attacker >= 0
            assert len(result.flavor_text) > 0


def test_intellect_technique_selection_counts():
    """Each fighter's technique count should match their base_intellect."""
    fighters = load_all_fighters("game/data/fighters")
    for f in fighters.values():
        assert 2 <= f.base_intellect <= 6
        # All fighters have 7 techniques, so intellect <= 7
        assert f.base_intellect <= len(f.technique_ids)


def test_intellect_in_combat_flow():
    """Full combat should work with intellect attribute and new techniques."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    ember = FighterInstance(fighter_data=fighters["ember"])
    anvil = FighterInstance(fighter_data=fighters["anvil"])

    # Ember has intellect 6 vs Anvil 3
    assert get_effective_intellect(ember) == 6
    assert get_effective_intellect(anvil) == 3

    # Both have speed 3, so Ember (higher intellect) should go first
    if ember.fighter_data.base_speed == anvil.fighter_data.base_speed:
        assert compare_speed_order(ember, anvil) == -1

    ember.selected_techniques = ["mind_over_matter", "confounding_blow", "immolating_insight"]
    anvil.selected_techniques = ["iron_wall", "giants_swing", "juggernaut_blow"]
    ember.selected_items = ["crown_of_whispers", "ring_of_cunning"]
    anvil.selected_items = ["iron_helm", "ring_of_vitality"]

    ember = apply_buffs(ember, items)
    anvil = apply_buffs(anvil, items)

    for a_act in [ActionType.STRIKE, ActionType.FEINT, ActionType.BLOCK]:
        for d_act in [ActionType.STRIKE, ActionType.COUNTER, ActionType.AVOID]:
            order = compare_speed_order(ember, anvil)
            if order <= 0:
                result = resolve_exchange(ember, anvil, a_act, d_act)
            else:
                result = resolve_exchange(anvil, ember, a_act, d_act)
            assert result.outcome in ("hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff", "assessed")
            assert result.flavor_text


def test_turn_limit_less_damage_wins():
    """After 17 volleys with both fighters alive, less damage taken wins."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    player_fighter = fighters["anvil"]
    ai_fighter = fighters["ember"]

    ai_instance = FighterInstance(fighter_data=ai_fighter)
    player_instance = FighterInstance(fighter_data=player_fighter)
    player_instance.selected_techniques = ["iron_wall", "giants_swing", "juggernaut_blow"]
    ai_instance.selected_techniques = ["flame_strike", "heat_wave", "immolating_insight"]

    player_instance = apply_buffs(player_instance, items)
    ai_instance = apply_buffs(ai_instance, items)

    # Boost HP so both survive 17 volleys of combat
    player_instance.current_health = 1000
    ai_instance.current_health = 1000

    match = MatchState(team_a=[player_instance], team_b=[ai_instance])
    for _ in range(4):
        match = advance_phase(match)

    assert match.phase == MatchPhase.COMBAT

    # Simulate volleys; turn limit via max_volleys=17 ends the round
    winner = None
    max_safe_volleys = 50
    volley_count = 0
    while match.phase == MatchPhase.COMBAT and volley_count < max_safe_volleys:
        for _ in range(3):
            # Use strike vs feint: attacker always hits for base power damage
            if compare_speed_order(player_instance, ai_instance) <= 0:
                result = resolve_exchange(
                    player_instance, ai_instance, ActionType.STRIKE, ActionType.FEINT
                )
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_attacker)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_defender)
                player_instance.damage_taken_this_round += result.damage_to_attacker
                ai_instance.damage_taken_this_round += result.damage_to_defender
            else:
                result = resolve_exchange(
                    ai_instance, player_instance, ActionType.STRIKE, ActionType.FEINT
                )
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_attacker)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_defender)
                ai_instance.damage_taken_this_round += result.damage_to_attacker
                player_instance.damage_taken_this_round += result.damage_to_defender

            if player_instance.current_health <= 0 or ai_instance.current_health <= 0:
                break

        clear_actions(match)
        winner = check_round_end(match, max_volleys=17)
        if winner:
            apply_round_result(match, winner)
            break
        volley_count += 1

    # Verify turn limit ended the round (not KO)
    assert match.phase == MatchPhase.ROUND_END
    assert match.current_volley == 17, "Turn limit of 17 volleys should have been reached"
    assert winner is not None, "A winner should have been determined"
    assert player_instance.current_health > 0, "Both fighters should survive turn limit"
    assert ai_instance.current_health > 0, "Both fighters should survive turn limit"

    # Winner should be the one who took less damage
    if winner != "draw":
        if winner == "a":
            assert player_instance.damage_taken_this_round < ai_instance.damage_taken_this_round
        else:
            assert ai_instance.damage_taken_this_round < player_instance.damage_taken_this_round
