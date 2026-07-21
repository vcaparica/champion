# Champion MVP Design Specification

Date: 2026-07-21
Status: Approved

## Overview

Champion is a turn-based online fighting game for blind and visually impaired players, built on an existing Pygame audiogame framework. Players choose fighters, customize them with techniques and magic items, and compete in 1v1 or 2v2 matches of best-of-3 rounds. The combat system is inspired by Burning Wheel Gold: players secretly declare actions in volleys of 3, trying to predict and counter their opponent's moves.

This document specifies the MVP scope, architecture, and design decisions.

## MVP Scope

- 4 fighters with full technique lists (8 each, 2 exclusive per fighter) and item panoplies (body slot items)
- 1v1 online matches with server-authoritative combat resolution
- Best-of-3 rounds match structure
- Full pre-match flow: fighter select, technique pick (3 of 8), item pick (2 from panoply)
- Combat engine with 6 base actions, interaction matrix, verbal positioning, and technique modifiers
- Accessible UI via screen reader throughout (existing Menu and AudioForm systems)
- Local AI opponent for offline play (basic random/predictive AI)
- 2v2 is out of scope for MVP, but the data model supports multi-combatant battles from day one

## Architecture

### Client

```
champion/
  main.py              (entry point)
  app.py               (Champion App with game-specific menu structure)
  menu.py              (accessible menu system, unchanged)
  audio_form.py        (accessible form system, unchanged)
  controls.py          (input management, unchanged)
  sr.py                (screen reader abstraction, unchanged)
  dj.py                (sound manager, unchanged)
  openal.py            (OpenAL wrapper, unchanged)
  dialogs.py           (Windows dialog helpers, unchanged)
  game/
    __init__.py
    fighter.py         (fighter data model, loader from JSON)
    technique.py       (technique definitions, effects)
    item.py            (item definitions, body slots, buffs)
    combat.py          (combat engine — action resolution, interaction matrix)
    match.py           (match state machine — phases, rounds, results)
    network.py         (client-side WebSocket connection)
    ai.py              (local AI opponent)
    data/
      fighters/        (JSON, one file per fighter)
      items/           (JSON, organized by slot)
      techniques/      (JSON, technique definitions)
  server/
    __init__.py
    main.py            (FastAPI + WebSocket entry point)
    match_manager.py   (lobby queue, pairing, match lifecycle)
    combat_resolver.py (server-side authoritative combat resolution)
    client_handler.py  (per-connection WebSocket handler)
    session.py         (player session management)
  snd/                 (audio assets, unchanged)
  docs/
    superpowers/
      specs/           (design documents)
```

### Server

- Python with FastAPI and WebSockets
- Server is sole authority for combat resolution, health tracking, range, advantage, debuffs
- Deterministic action resolution using the interaction matrix with technique/item modifiers
- Both clients receive identical results; client only handles presentation via screen reader

### Communication Protocol

JSON over WebSocket. Client-to-server messages:

| Type | Fields | Purpose |
|------|--------|---------|
| join_queue | mode | Enter matchmaking |
| select_fighter | fighter_id | Pick fighter for match |
| select_techniques | technique_ids (3) | Pick techniques for match |
| select_items | item_ids (2) | Pick items for match |
| declare_actions | actions (3 with target_id) | Submit volley actions |
| ready_for_next_round | | Confirm between rounds |

Server-to-client messages:

| Type | Fields | Purpose |
|------|--------|---------|
| match_found | match_id, opponent_name | Match is ready |
| phase_change | phase | Advance match phase |
| volley_result | exchanges (3) | Combat resolution |
| match_over | winner, stats | Match conclusion |

## Combat System

### Base Actions

Six action types. Each volley a player declares 3 actions in secret, then they resolve simultaneously exchange by exchange.

1. **Strike** — direct attack, deals damage on success
2. **Block** — defensive stance, negates incoming Strikes and Charges
3. **Feint** — deceptive move, bypasses Blocks but vulnerable to quick Strikes
4. **Counter** — reactive strike, punishes Charges and Feints but loses to Blocks
5. **Charge** — powerful committed attack, breaks Blocks but slow, loses to Counter and Avoid
6. **Avoid** — evasive maneuver, dodges Strikes and Charges but caught by Feints

### Action Interaction Rules

1. Strike hits Feint and Avoid. Strike is blocked by Block. Strike is countered by Counter. Strike is beaten by Charge (faster/longer reach). Strike vs Strike is a clash — both take reduced damage.
2. Block stops Strike, Counter, and Charge. Block is bypassed by Feint. Block vs Block has no effect.
3. Feint beats Block, Counter, and Avoid. Feint loses to Strike and Charge. Feint vs Feint is a clash — neither lands cleanly.
4. Counter beats Strike and Charge (punishes committed attacks). Counter loses to Block and Feint. Counter vs Counter — both whiff.
5. Charge beats Strike (reach/power advantage) and breaks Block. Charge loses to Counter (telegraphed) and Avoid (too slow). Charge vs Charge is a heavy clash — both take amplified damage.
6. Avoid dodges Strike and Charge. Avoid is caught by Feint (read the dodge). Avoid vs Avoid — both reposition, range may shift.

Clash resolution: when both fighters use the same aggressive action, the fighter with higher speed deals partial damage and takes partial damage. Blocks cancel each other out harmlessly.

### Positioning System

No grid. Verbal descriptors only, designed for audio presentation.

**Range:** close, medium, far. Certain actions change range. Some techniques require or ignore range. Default starting range is medium.

**Advantage:** neutral, offensive edge, defensive edge. Winning exchanges shifts advantage toward the winner. Advantage modifies damage dealt and taken. Some techniques grant advantage directly.

### Techniques

Each technique references a base action and adds modifiers. Techniques do not consume resources. Their drawback: each use increases predictability, making it easier for the opponent to anticipate future actions.

Technique structure:
- name, description
- base_action (one of the 6 action types)
- effects: any combination of damage_modifier, bypass_range, heal_on_hit, reposition (set range), apply_debuff, steal_item, switch_own_item, gain_advantage, multi_target
- predictability_increase: how much this technique telegraphs future actions

### Items

Items occupy body slots and provide passive buffs or reactive triggers. They do not generate actions.

**Body slots:** head, eyes, neck, torso, body, shoulders, arms, hands, ring1, ring2, waist, feet. Most fighters have 2 ring slots; some may have fewer or more.

**Passive effects:** health_modifier, power_modifier, speed_modifier, damage_reduction, resist_debuff_type

**Reactive triggers:** when_struck (counter-damage), when_hit_by_technique (damage reduction), when_avoid_success (gain advantage), when_low_health (heal or buff)

## Fighter Model

Stored as JSON per fighter:

- id, name, description
- base_stats: health, speed, power
- technique_ids: list of 8 technique references. Exactly 2 are exclusive to this fighter
- panoply: item_ids organized by body slot, 1-3 options per slot

## Match Flow

1. Lobby — players connect, form a 1v1 match
2. Fighter select — each player picks from the 4-fighter roster
3. Technique select — pick 3 of 8 techniques, hidden from opponent
4. Item select — pick 2 items from panoply
5. Round 1 — combat begins, volleys until a fighter reaches 0 health
6. Between rounds — brief intermission
7. Rounds 2 and 3 as needed — best of 3 wins
8. Results — winner announced, return to lobby

## 2v2 Forward Compatibility

The MVP implements 1v1 only, but the architecture supports future 2v2 battles where all four fighters act simultaneously, each able to target any opponent, with turn order interleaving by fighter speed.

Design decisions that preserve this path:

- Action target field — every action declaration includes a target_id. In 1v1 it is always the single opponent. In 2v2 it selects among opponents.
- Combatant lists — matches store team_a: list of fighter instances and team_b: list of fighter instances, not single fighters. MVP populates each list with one entry.
- Turn order queue — the engine sorts all combatants by speed each volley. Future 2v2 interleaves turns across teams naturally.
- Volley declarations — each player declares 3 actions for their fighter. Resolution processes all declared actions in speed order across all combatants, not grouped by team.

## Project Transformation Tasks

Before implementation begins, the template must become the Champion project:

- Change window title from "Audiogame Template" to "Champion"
- Update file headers from template references to Champion project
- Remove GameSettingsForm (demo/sample code)
- Clean git: no remote exists, so create fresh history on main branch
- Commit initial project state
- Set up remote and push

## Error Handling

- Network disconnects: client shows reconnection dialog, server preserves match state for 60 seconds
- Invalid actions: server rejects and requests re-submission
- Audio fallback: DJ system already handles missing OGG (falls back to WAV), no changes needed
- Screen reader unavailable: speech functions fail silently, game remains playable via existing audio cues

## Testing Strategy

No test framework exists in the project. For MVP:

- Combat resolver gets standalone unit tests (pure logic, no dependencies)
- Fighter/item/technique loading tested via JSON schema validation
- Client-server protocol tested via pytest with FastAPI TestClient for WebSocket
- Manual testing for screen reader output and audio feedback

## Dependencies

Existing: pygame, cytolk, openal (bundled), pyogg (optional), pyperclip (optional)
New for MVP: fastapi, uvicorn, websockets
