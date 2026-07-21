# Round Pause, Match Announcements, and Turn Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add round-win pause, match-start announcements, and a 17-volley turn limit with damage-taken tiebreaker to both local and online play.

**Architecture:** Add `damage_taken_this_round` field to `FighterInstance`, extend `check_round_end` with an optional `max_volleys` parameter, add `_wait_for_continue` pauses after round wins and before first volley, and announce matchup/round info. Mirrors local-play changes in the server-side combat resolver.

**Tech Stack:** Python 3, pytest, pygame (local client), FastAPI (server)

## Global Constraints

- All announcements via `speak()` screen reader, following existing `interrupt=True` pattern
- Pauses use `_wait_for_continue(repeat_text=...)` — Enter/Space to continue, R to repeat, Escape/Alt+F4 to quit
- 17 volleys per round maximum; tie on damage taken is a draw
- Match-start announcement only before round 1; subsequent rounds announce round number only
- Damage tracking resets each round via `reset_for_new_round`

---

### Task 1: Add damage_taken_this_round field to FighterInstance

**Files:**
- Modify: `game/combat.py`

**Interfaces:**
- Produces: `FighterInstance.damage_taken_this_round: int = 0` (default in dataclass field)

- [ ] **Step 1: Add the field to FighterInstance dataclass**

In `game/combat.py`, in the `FighterInstance` dataclass, add the field after `intellect_modifier`:

```python
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
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `pytest tests/ -v`
Expected: All 52+ tests PASS (new field defaults to 0 and doesn't break any existing assertions)

- [ ] **Step 3: Commit**

```bash
git add game/combat.py
git commit -m "feat: add damage_taken_this_round field to FighterInstance"
```

---

### Task 2: Reset damage_taken_this_round in reset_for_new_round

**Files:**
- Modify: `game/match.py`

**Interfaces:**
- Consumes: `FighterInstance.damage_taken_this_round` (from Task 1)

- [ ] **Step 1: Add reset of damage_taken_this_round**

In `game/match.py`, in `reset_for_new_round`, add `fighter.damage_taken_this_round = 0` to the existing loop:

```python
def reset_for_new_round(match: MatchState) -> MatchState:
    """Reset combatants for a new round."""
    for fighter in match.team_a + match.team_b:
        fighter.current_health = fighter.fighter_data.base_health * 10
        fighter.current_range = Range.MEDIUM
        fighter.current_advantage = Advantage.NEUTRAL
        fighter.active_debuffs = []
        fighter.predictability = 0
        fighter.power_modifier = 0
        fighter.speed_modifier = 0
        fighter.intellect_modifier = 0
        fighter.damage_reduction = 0
        fighter.damage_taken_this_round = 0
    match.phase = MatchPhase.COMBAT
    match.current_volley = 0
    return match
```

- [ ] **Step 2: Run existing tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add game/match.py
git commit -m "feat: reset damage_taken_this_round in reset_for_new_round"
```

---

### Task 3: Write tests for turn limit in check_round_end

**Files:**
- Modify: `tests/test_match.py`

**Interfaces:**
- Consumes: `check_round_end(match, max_volleys=None)` (signature to be implemented in Task 4)

- [ ] **Step 1: Write failing tests**

Add these test functions to `tests/test_match.py`:

```python
def test_check_round_end_turn_limit_less_damage_wins():
    """At turn limit, fighter who took less damage should win."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 17
    # Both alive, but A took less damage
    match.team_a[0].damage_taken_this_round = 10
    match.team_b[0].damage_taken_this_round = 25
    assert check_round_end(match, max_volleys=17) == "a"


def test_check_round_end_turn_limit_team_b_wins():
    """At turn limit, team B wins if fighter B took less damage."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 17
    match.team_a[0].damage_taken_this_round = 30
    match.team_b[0].damage_taken_this_round = 5
    assert check_round_end(match, max_volleys=17) == "b"


def test_check_round_end_turn_limit_equal_damage_draw():
    """At turn limit, equal damage taken should be a draw."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 17
    match.team_a[0].damage_taken_this_round = 20
    match.team_b[0].damage_taken_this_round = 20
    assert check_round_end(match, max_volleys=17) == "draw"


def test_check_round_end_turn_limit_not_reached():
    """Before turn limit, health-based check should still work normally."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 10
    match.team_a[0].damage_taken_this_round = 5
    match.team_b[0].damage_taken_this_round = 50
    # Turn limit not reached, both alive, so no winner
    assert check_round_end(match, max_volleys=17) is None


def test_check_round_end_health_zero_still_wins():
    """Health reaching zero should still win even before turn limit."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.current_volley = 5
    match.team_b[0].current_health = 0
    # Health-based win takes priority
    assert check_round_end(match, max_volleys=17) == "a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_match.py::test_check_round_end_turn_limit_less_damage_wins tests/test_match.py::test_check_round_end_turn_limit_team_b_wins tests/test_match.py::test_check_round_end_turn_limit_equal_damage_draw tests/test_match.py::test_check_round_end_turn_limit_not_reached tests/test_match.py::test_check_round_end_health_zero_still_wins -v`
Expected: FAIL — check_round_end doesn't accept max_volleys yet, or new tests fail on assertion

- [ ] **Step 3: Commit**

```bash
git add tests/test_match.py
git commit -m "test: add turn limit and damage-taken tests for check_round_end"
```

---

### Task 4: Implement turn limit logic in check_round_end

**Files:**
- Modify: `game/match.py`

**Interfaces:**
- Consumes: `FighterInstance.damage_taken_this_round` (from Task 1), `MatchState.current_volley`
- Produces: `check_round_end(match, max_volleys: Optional[int] = None) -> Optional[str]`

- [ ] **Step 1: Update check_round_end signature and logic**

In `game/match.py`, replace the existing `check_round_end` function:

```python
def check_round_end(match: MatchState, max_volleys: Optional[int] = None) -> Optional[str]:
    """Check if the round is over. Returns winning team ('a' or 'b') or None.

    Args:
        match: The current match state.
        max_volleys: If set, the round ends at this volley count with the
            fighter who took less damage declared the winner. Draw if equal.

    Returns:
        'a', 'b', 'draw', or None.
    """
    if match.phase != MatchPhase.COMBAT:
        return None

    a_alive = any(f.current_health > 0 for f in match.team_a)
    b_alive = any(f.current_health > 0 for f in match.team_b)

    # Health-based win takes priority
    if not a_alive and not b_alive:
        return "draw"
    if not b_alive:
        return "a"
    if not a_alive:
        return "b"

    # Turn limit check
    if max_volleys is not None and match.current_volley >= max_volleys:
        a_damage = sum(f.damage_taken_this_round for f in match.team_a)
        b_damage = sum(f.damage_taken_this_round for f in match.team_b)
        if a_damage < b_damage:
            return "a"
        if b_damage < a_damage:
            return "b"
        return "draw"

    return None
```

- [ ] **Step 2: Run the new tests to verify they pass**

Run: `pytest tests/test_match.py -v`
Expected: All tests PASS (existing + 5 new turn-limit tests)

- [ ] **Step 3: Commit**

```bash
git add game/match.py
git commit -m "feat: add max_volleys turn limit to check_round_end"
```

---

### Task 5: Track damage taken in local combat volley

**Files:**
- Modify: `app.py` (`_run_combat_volley`)

**Interfaces:**
- Consumes: `FighterInstance.damage_taken_this_round` (from Task 1)

- [ ] **Step 1: Add damage tracking to _run_combat_volley**

In `app.py`, in `_run_combat_volley`, after applying damage to both fighters in each exchange, add to `damage_taken_this_round`. The method has two branches (player-first and AI-first in the speed-order check). Update both:

For the `order <= 0` branch (player attacks first), after:
```python
                player.current_health = a_health
                ai.current_health = d_health
```
Add:
```python
                player.damage_taken_this_round += result.damage_to_attacker
                ai.damage_taken_this_round += result.damage_to_defender
```

For the `order > 0` branch (AI attacks first), after:
```python
                ai.current_health = a_health
                player.current_health = d_health
```
Add:
```python
                ai.damage_taken_this_round += result.damage_to_attacker
                player.damage_taken_this_round += result.damage_to_defender
```

The full updated `_run_combat_volley` method becomes:

```python
    def _run_combat_volley(self, match) -> None:
        """Run one volley (3 actions) of combat for local play."""
        from game.combat import resolve_exchange, get_effective_speed, compare_speed_order
        from game.ai import choose_ai_actions

        player = match.team_a[0]
        ai = match.team_b[0]

        # Player declares 3 actions
        player_actions = self._declare_actions_screen(player, ai)
        if player_actions is None:
            return

        # AI declares 3 actions
        ai_actions = choose_ai_actions(ai, player, player.predictability, self.techniques)

        # Resolve each exchange
        for i in range(3):
            p_act = player_actions[i]
            try:
                p_action_type = ActionType(p_act["action"])
            except ValueError:
                p_action_type = ActionType.STRIKE
            try:
                ai_action_type = ActionType(ai_actions[i]["action"])
            except ValueError:
                ai_action_type = ActionType.STRIKE

            # Look up technique data for both fighters
            p_tech_id = p_act.get("technique_id")
            ai_tech_id = ai_actions[i].get("technique_id")
            p_technique = self.techniques.get(p_tech_id) if p_tech_id else None
            ai_technique = self.techniques.get(ai_tech_id) if ai_tech_id else None

            order = compare_speed_order(player, ai)
            if order <= 0:  # player goes first (or tie — player preference)
                result = resolve_exchange(
                    player, ai, p_action_type, ai_action_type,
                    attacker_technique=p_technique, defender_technique=ai_technique
                )
                attacker_name = player.fighter_data.name
                defender_name = ai.fighter_data.name
                attacker_action = p_action_type.value
                defender_action = ai_action_type.value
                a_health = max(0, player.current_health - result.damage_to_attacker)
                d_health = max(0, ai.current_health - result.damage_to_defender)
                player.current_health = a_health
                ai.current_health = d_health
                player.damage_taken_this_round += result.damage_to_attacker
                ai.damage_taken_this_round += result.damage_to_defender
            else:
                result = resolve_exchange(
                    ai, player, ai_action_type, p_action_type,
                    attacker_technique=ai_technique, defender_technique=p_technique
                )
                attacker_name = ai.fighter_data.name
                defender_name = player.fighter_data.name
                attacker_action = ai_action_type.value
                defender_action = p_action_type.value
                a_health = max(0, ai.current_health - result.damage_to_attacker)
                d_health = max(0, player.current_health - result.damage_to_defender)
                ai.current_health = a_health
                player.current_health = d_health
                ai.damage_taken_this_round += result.damage_to_attacker
                player.damage_taken_this_round += result.damage_to_defender

            exchange_text = self._announce_exchange(
                i, result, attacker_name, defender_name, a_health, d_health,
                attacker_action=attacker_action, defender_action=defender_action
            )
            self._wait_for_continue(repeat_text=exchange_text)

            if not self.running:
                return

            if player.current_health <= 0 or ai.current_health <= 0:
                break
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: track damage_taken_this_round in local combat volley"
```

---

### Task 6: Add round-win pause and announcements to local play

**Files:**
- Modify: `app.py` (`_on_local_match`)

**Interfaces:**
- Consumes: `check_round_end(match, max_volleys=17)` (from Task 4), `_wait_for_continue`, `_announce_round_result`
- Produces: (no new interfaces, modifies existing flow)

- [ ] **Step 1: Update _on_local_match with pause, announcements, and turn limit**

Replace the `_on_local_match` method's combat loop section. The current code (lines 288-307) becomes:

```python
        # Run combat
        from game.ai import choose_ai_actions

        # Match-start announcement
        p_name = match.team_a[0].fighter_data.name
        ai_name = match.team_b[0].fighter_data.name
        speak(f"{p_name} versus {ai_name}! Fight!", True)
        if not self._wait_for_continue():
            return

        while match.phase == MatchPhase.COMBAT:
            self._run_combat_volley(match)
            if not self.running:
                break
            from game.match import check_round_end, apply_round_result, clear_actions
            winner = check_round_end(match, max_volleys=17)
            if winner:
                apply_round_result(match, winner)
                # Announce time up for turn-limit wins
                if winner != "draw" and all(
                    f.current_health > 0 for f in match.team_a + match.team_b
                ):
                    speak("Time up!", True)
                self._announce_round_result(match, winner)
                # Pause for player to process round result
                if not self._wait_for_continue():
                    break
                from game.match import check_match_end, reset_for_new_round
                match_winner = check_match_end(match)
                if match_winner:
                    self._announce_match_result(match, match_winner)
                    break
                if match.phase != MatchPhase.MATCH_END:
                    reset_for_new_round(match)
                    # Announce next round
                    speak(f"Round {match.round_number + 1}, fight!", True)
                    if not self._wait_for_continue():
                        break
            else:
                clear_actions(match)
```

Key changes:
- Match-start announcement before the combat loop: "{Fighter A} versus {Fighter B}! Fight!"
- Pause after match-start announcement
- `check_round_end(match, max_volleys=17)` — passes turn limit
- "Time up!" announcement when turn limit triggers (both fighters still alive)
- `_wait_for_continue()` after round result announcement
- Round-start announcement after reset: "Round {N}, fight!"
- Pause after round-start announcement

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (the combat flow tests don't call `_wait_for_continue` directly)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add round-win pause, match-start and round-start announcements, 17-volley limit to local play"
```

---

### Task 7: Track damage taken in server combat resolver

**Files:**
- Modify: `server/combat_resolver.py`

**Interfaces:**
- Consumes: `FighterInstance.damage_taken_this_round` (from Task 1)

- [ ] **Step 1: Add damage tracking to resolve_volley_server**

In `server/combat_resolver.py`, in `resolve_volley_server`, add damage tracking in both speed-order branches.

For the `order <= 0` branch, after applying health damage:
```python
            # Apply damage
            defender.current_health = max(0, defender.current_health - result.damage_to_defender)
            attacker.current_health = max(0, attacker.current_health - result.damage_to_attacker)
```
Add:
```python
            attacker.damage_taken_this_round += result.damage_to_attacker
            defender.damage_taken_this_round += result.damage_to_defender
```

For the `order > 0` branch, after applying health damage:
```python
            attacker.current_health = max(0, attacker.current_health - result.damage_to_defender)
            defender.current_health = max(0, defender.current_health - result.damage_to_attacker)
```
Add:
```python
            attacker.damage_taken_this_round += result.damage_to_defender
            defender.damage_taken_this_round += result.damage_to_attacker
```

Full updated `resolve_volley_server`:

```python
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

        a_technique = None
        b_technique = None

        order = compare_speed_order(attacker, defender)
        if order <= 0:
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
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (server code not directly tested by current test suite)

- [ ] **Step 3: Commit**

```bash
git add server/combat_resolver.py
git commit -m "feat: track damage_taken_this_round in server combat resolver"
```

---

### Task 8: Pass max_volleys to check_round_end on server

**Files:**
- Modify: `server/match_manager.py`

**Interfaces:**
- Consumes: `check_round_end(match, max_volleys=17)` (from Task 4)

- [ ] **Step 1: Update resolve_volley to pass max_volleys=17**

In `server/match_manager.py`, in `resolve_volley`, change the `check_round_end` call:

```python
    def resolve_volley(self, match_id: str, player_id: str, actions: list) -> dict:
        match = self._matches.get(match_id)
        if not match:
            return {"type": "error", "message": "Match not found"}

        team = self.get_player_team(match, player_id)
        if team == "a":
            match.match_state.actions_declared_a = actions
        else:
            match.match_state.actions_declared_b = actions

        from game.match import all_actions_declared
        if not all_actions_declared(match.match_state):
            return {"type": "actions_received", "team": team}

        from server.combat_resolver import resolve_volley_server
        result = resolve_volley_server(match)

        from game.match import clear_actions, check_round_end, apply_round_result
        clear_actions(match.match_state)

        round_winner = check_round_end(match.match_state, max_volleys=17)
        if round_winner:
            apply_round_result(match.match_state, round_winner)
            from game.match import check_match_end
            match_winner = check_match_end(match.match_state)
            result["round_end"] = True
            result["round_winner"] = round_winner
            if match_winner:
                result["match_end"] = True
                result["match_winner"] = match_winner

        return result
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add server/match_manager.py
git commit -m "feat: pass max_volleys=17 to check_round_end on server"
```

---

### Task 9: Add round-win pause and announcements to online play client

**Files:**
- Modify: `app.py` (`_on_play_online`)

- [ ] **Step 1: Update _on_play_online with round-end pause and round-start announcements**

Replace the combat section of `_on_play_online` (from "Combat begins!" through the combat loop):

```python
        speak("Combat begins! Declare your actions carefully.", True)

        # Match-start announcement
        opp_name = "Opponent"  # We don't know the opponent's fighter name yet
        speak(f"{fighter.name} versus opponent! Fight!", True)
        if not self._wait_for_continue():
            client.close()
            return

        # Combat loop
        round_num = 0
        rounds_won_player = 0
        rounds_won_opponent = 0

        while client.is_connected:
            # Declare 3 actions
            opponent_health = "unknown"
            player_actions = self._declare_actions_screen(
                player_instance,
                FighterInstance(fighter_data=fighter)  # placeholder for speech only
            )
            if player_actions is None:
                client.close()
                return

            client.send({"type": "declare_actions", "actions": player_actions})
            speak("Waiting for opponent's actions...", False)

            # Wait for volley result
            msg = self._wait_for_message(client, "volley_result", timeout=60.0)
            if msg is None:
                speak("Connection lost during combat.", True)
                client.close()
                return

            exchanges = msg.get("exchanges", [])
            for i, ex in enumerate(exchanges):
                flavor = ex.get("flavor_text", "")
                attacker = ex.get("attacker_name", "Unknown")
                defender = ex.get("defender_name", "Unknown")
                a_hp = ex.get("attacker_health", 0)
                d_hp = ex.get("defender_health", 0)
                text = (f"Exchange {i + 1}: {flavor} "
                        f"{attacker} health: {a_hp}. {defender} health: {d_hp}.")
                speak(text, True)
                pygame.time.wait(500)

            # Check for round/match end
            if msg.get("round_end"):
                round_winner = msg.get("round_winner", "draw")
                time_up = msg.get("time_up", False)
                if time_up:
                    speak("Time up!", True)
                if round_winner == "a":
                    rounds_won_player += 1
                    speak(f"You win round {round_num + 1}!", True)
                elif round_winner == "b":
                    rounds_won_opponent += 1
                    speak(f"Opponent wins round {round_num + 1}!", True)
                else:
                    speak(f"Round {round_num + 1} is a draw!", True)
                round_num += 1

                # Pause for player to process
                if not self._wait_for_continue():
                    client.close()
                    return

                if msg.get("match_end"):
                    match_winner = msg.get("match_winner", "draw")
                    if match_winner == "a":
                        speak("Victory! You win the match!", True)
                    else:
                        speak("Defeat! Your opponent wins the match!", True)
                    break

                speak(f"Score: You {rounds_won_player} - {rounds_won_opponent} Opponent. Round {round_num + 1}, fight!", False)
                if not self._wait_for_continue():
                    client.close()
                    return
                client.send({"type": "ready_for_next_round"})
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add round-win pause and match-start announcement to online play"
```

---

### Task 10: Add time_up field to server volley result when turn limit triggers

**Files:**
- Modify: `server/match_manager.py`

- [ ] **Step 1: Include time_up in volley result when turn limit triggers**

In `server/match_manager.py`, in `resolve_volley`, after detecting round_winner, check if both fighters are still alive (indicating turn-limit win):

```python
        round_winner = check_round_end(match.match_state, max_volleys=17)
        if round_winner:
            # Check if this was a turn-limit win (both fighters still alive)
            a_alive = any(f.current_health > 0 for f in match.match_state.team_a)
            b_alive = any(f.current_health > 0 for f in match.match_state.team_b)
            if a_alive and b_alive and round_winner != "draw":
                result["time_up"] = True
            apply_round_result(match.match_state, round_winner)
            from game.match import check_match_end
            match_winner = check_match_end(match.match_state)
            result["round_end"] = True
            result["round_winner"] = round_winner
            if match_winner:
                result["match_end"] = True
                result["match_winner"] = match_winner
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add server/match_manager.py
git commit -m "feat: add time_up flag to server volley result on turn limit"
```

---

### Task 11: Integration test for turn limit

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Add integration test for turn limit**

Add this test to `tests/test_integration.py`:

```python
def test_turn_limit_less_damage_wins():
    """After 17 volleys with both fighters alive, less damage taken wins."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    player_fighter = fighters["thorn"]
    ai_fighter = fighters["ember"]

    ai_instance = FighterInstance(fighter_data=ai_fighter)
    player_instance = FighterInstance(fighter_data=player_fighter)
    player_instance.selected_techniques = ["iron_wall", "shield_bash", "war_cry"]
    ai_instance.selected_techniques = ["fireball", "inferno", "heat_wave"]

    player_instance = apply_buffs(player_instance, items)
    ai_instance = apply_buffs(ai_instance, items)

    match = MatchState(team_a=[player_instance], team_b=[ai_instance])
    for _ in range(4):
        match = advance_phase(match)

    assert match.phase == MatchPhase.COMBAT

    # Simulate 17 volleys with tiny damage (only action outcomes that deal damage)
    volley_count = 0
    while match.phase == MatchPhase.COMBAT and volley_count < 17:
        from game.match import check_round_end, apply_round_result, clear_actions
        for i in range(3):
            # Use strike vs feint to guarantee hits but make them weak
            if compare_speed_order(player_instance, ai_instance) <= 0:
                result = resolve_exchange(player_instance, ai_instance, ActionType.STRIKE, ActionType.FEINT)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_attacker)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_defender)
                player_instance.damage_taken_this_round += result.damage_to_attacker
                ai_instance.damage_taken_this_round += result.damage_to_defender
            else:
                result = resolve_exchange(ai_instance, player_instance, ActionType.STRIKE, ActionType.FEINT)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_attacker)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_defender)
                ai_instance.damage_taken_this_round += result.damage_to_attacker
                player_instance.damage_taken_this_round += result.damage_to_defender

            if player_instance.current_health <= 0 or ai_instance.current_health <= 0:
                break

        winner = check_round_end(match, max_volleys=17)
        if winner:
            apply_round_result(match, winner)
            break
        clear_actions(match)
        volley_count += 1

    # Should have ended due to turn limit or health
    assert match.phase == MatchPhase.ROUND_END
    # Both fighters should still have health (turn limit ended it)
    # If turn limit triggered, winner should be the one who took less damage
    if winner != "draw":
        if winner == "a":
            assert player_instance.damage_taken_this_round < ai_instance.damage_taken_this_round
        else:
            assert ai_instance.damage_taken_this_round < player_instance.damage_taken_this_round
```

- [ ] **Step 2: Run the integration test**

Run: `pytest tests/test_integration.py::test_turn_limit_less_damage_wins -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for 17-volley turn limit"
```
