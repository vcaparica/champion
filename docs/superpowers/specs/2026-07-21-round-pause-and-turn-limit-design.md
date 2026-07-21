# Round Pause, Match Announcements, and Turn Limit

Date: 2026-07-21
Status: design

## Context

Champion is a turn-based online fighting game for blind and visually impaired players. Combat happens in volleys of 3 exchanges using rock-paper-scissors style action pairs. Matches are best-of-3 rounds.

## Features

### 1. Round Win Pause

After a round ends (one fighter's health reaches 0), the game announces the winner and pauses. The player must press Enter or Space to continue to the next round. This gives the player time to process the round result before the next round begins.

This applies to both local and online play.

### 2. Match-Start and Round-Start Announcements

At the very start of a match, before action declaration for the first volley, the game announces the matchup and pauses. Announcement format: "{Fighter A} versus {Fighter B}! Fight!"

For subsequent rounds (2 and 3), after the round-winner pause, the game announces "Round {N}, fight!" before entering action declaration.

These pauses use the existing `_wait_for_continue` system (Enter/Space to continue, R to repeat, Escape/Alt+F4 to quit).

### 3. 17-Volley Turn Limit

Each round has a maximum of 17 volleys. If a round reaches the 17th volley without either fighter's health reaching 0, the round ends and the winner is the fighter who took less damage during that round (not the fighter with more remaining health).

If both fighters took exactly the same amount of damage, the round is a draw (no one gets a point).

Announcement: "Time up! {Winner} wins the round!" (no mention of damage comparison in the announcement).

## Design

### Damage Tracking

**New field on `FighterInstance` (game/combat.py):**
```python
damage_taken_this_round: int = 0
```

This accumulates all damage received by the fighter during the current round.

**Increment damage:** In `_run_combat_volley` (app.py) and `resolve_volley_server` (server/combat_resolver.py), after each exchange, add the damage dealt to the defender's `damage_taken_this_round`.

**Reset:** In `reset_for_new_round` (game/match.py), set `damage_taken_this_round = 0` alongside the existing health/modifier resets.

### Turn Limit Logic (game/match.py)

Modify `check_round_end` to accept an optional `max_volleys` parameter:

```python
def check_round_end(match: MatchState, max_volleys: Optional[int] = None) -> Optional[str]:
```

Logic:
1. Check if either fighter's health is 0 (existing logic). If yes, return winner.
2. If `max_volleys` is set and `match.current_volley >= max_volleys`:
   - Compare `damage_taken_this_round` across fighters
   - Fighter who took less damage wins the round
   - If equal, return `"draw"`

Callers pass `max_volleys=17`:
- `_on_local_match` in app.py
- `resolve_volley` in `server/match_manager.py`

### Round Win Pause (app.py)

**Local play (`_on_local_match`):**
After `_announce_round_result()` and before `check_match_end()`: call `_wait_for_continue()`.

**Online play (`_on_play_online`):**
The round-end announcement already happens. Add a `_wait_for_continue()` call after the round-end speech before sending `ready_for_next_round`.

### Match-Start and Round-Start Announcements (app.py)

**Local play (`_on_local_match`):**
After advancing to COMBAT phase and before the combat loop:
```
speak("{Fighter A} versus {Fighter B}! Fight!", True)
_wait_for_continue()
```

At the start of each subsequent round (after `reset_for_new_round`):
```
speak(f"Round {match.round_number + 1}, fight!", True)
```

**Online play (`_on_play_online`):**
On first entering combat after receiving match_found and completing setup, announce the matchup. On subsequent `round_end` messages, after the round-winner pause, announce the next round number.

### Files Changed

- `game/combat.py` — add `damage_taken_this_round` to `FighterInstance`
- `game/match.py` — modify `check_round_end` for turn limit; add `damage_taken_this_round` reset in `reset_for_new_round`
- `app.py` — damage tracking in `_run_combat_volley`, round win pause, match-start and round-start announcements
- `server/combat_resolver.py` — damage tracking in `resolve_volley_server`
- `server/match_manager.py` — pass `max_volleys=17` to `check_round_end`

## Testing

- Integration test: round ends at volley 17 when both fighters survive, less-damage fighter wins
- Integration test: round ends at volley 17 with equal damage → draw
- Integration test: round ends before volley 17 via health depletion (existing behavior preserved)
- Manual: press Enter/Space to advance past round-win pause
- Manual: hear matchup announcement before first volley
