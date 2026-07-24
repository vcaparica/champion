# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Champion is a turn-based online fighting game for blind and visually impaired players, built on Pygame with screen reader integration (NVDA/JAWS/SAPI via cytolk), spatial audio (OpenAL), and gamepad support. Players choose fighters, customize them with techniques and magic items, and compete in 1v1 matches of best-of-3 rounds. The combat system is inspired by Burning Wheel Gold: players secretly declare actions in volleys of 3, trying to predict and counter their opponent's moves.

**Repository:** `https://github.com/vcaparica/champion` — main branch

## Running

### Client (local play vs AI)
```bash
python main.py
```

### Server (online play)
```bash
pip install fastapi uvicorn websockets
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### Tests
```bash
pytest tests/ -v    # 296 tests across 25 test files
```

### Dependencies
- **Required:** `pygame`, `cytolk`
- **Optional:** `pyogg` (OGG audio, falls back to WAV), `pyperclip` (clipboard in forms)
- **Server:** `fastapi`, `uvicorn`, `websockets`
- **Testing:** `pytest`

## Architecture

**Entry flow:** `main.py` → `App` (app.py) → `App.main_menu()` → game loop

### Framework layer (unchanged from template)

- **Menu / MenuItem** (menu.py) — Accessible menu system with keyboard/gamepad navigation, type-ahead search, item wrapping, checkboxes, radio buttons, and sliders. `Menu.run()` enters a blocking loop and returns the selected item result. Enhanced with boundary/wrap SFX support.
- **AudioForm** (audio_form.py) — Dialog/form system with buttons, input boxes, lists, checkboxes, and progress bars. Enhanced with list orientation, wrap, and type-ahead search.
- **GameControls** (controls.py) — Unified input handling for keyboard, mouse, and gamepad. Uses `InputState` enum (RELEASED → PRESSED → HELD → JUST_RELEASED) with per-frame `update()` calls. **Important:** check keys with `is_key_pressed()` BEFORE calling `update()`, since `update()` transitions PRESSED → HELD.
- **DJ** (dj.py) — Sound manager for SFX and BGM. Loads from `snd/sfx/` and `snd/bgm/`. Supports 3D panning via `play_sfx(name, x=position)`. Uses OpenAL.
- **sr** (sr.py) — Screen reader speech abstraction via Tolk/cytolk. Key functions: `speak(text, interrupt=True/False)`, `silence()`, `braille()`.
- **openal.py** — Low-level OpenAL C++ binding wrapper (from pyglet). Not typically modified.
- **dialogs.py** — Windows native dialog helpers (alert, question, input boxes via Win32 API).

### Game logic layer (`game/`)

- **game/enums.py** — Shared enumerations: `ActionType` (strike, block, feint, counter, charge, avoid), `Range` (close, medium, far), `Advantage` (neutral, offensive, defensive), `BodySlot` (11 slots), `MatchPhase`, `BuffType`, `DebuffType`
- **game/fighter.py** — `FighterData` dataclass, `load_fighter()`, `load_all_fighters()` JSON loader
- **game/technique.py** — `TechniqueData`, `TechniqueEffect` dataclasses, JSON loader. Techniques modify base actions with damage modifiers, debuffs, healing, repositioning, advantage changes, etc.
- **game/item.py** — `ItemData`, `ItemBuff`, `ItemReactive` dataclasses, JSON loader. Items occupy body slots providing passive buffs and reactive triggers.
- **game/combat.py** — Core combat engine. `FighterInstance` (runtime fighter state), `ExchangeResult` (outcome of one action pair), `resolve_exchange()` (36-pair interaction matrix), `apply_buffs()`, `get_effective_speed()`, `get_effective_power()`, `compute_damage()`
- **game/reactions.py** — Reactive engine: `Trigger` enum, `ReactionContext`, `fire()` dispatcher, `attach_reactions()`, item-reactive adapter, and volley helpers (`tick_burn`, `commit_damage`, `fire_low_health`, `clear_volley_state`). Powers fighter Feats and activates item reactives.
- **game/feat.py** — `Feat`, `Reaction` dataclasses and JSON loader. One innate Feat per fighter.
- **game/match.py** — `MatchState` dataclass tracking phase, rounds, action declarations, victory conditions. Functions: `advance_phase()`, `declare_actions()`, `all_actions_declared()`, `check_round_end()`, `check_match_end()`, `reset_for_new_round()`
- **game/ai.py** — AI opponent: `choose_ai_actions()` (3 per volley with predictability-based counter-picking), `choose_ai_techniques()` (base_intellect-based from 7-technique pool), `choose_ai_items()` (scoring heuristic, capped at base_speed), `choose_ai_fighter()`
- **game/network.py** — `GameClient` class: WebSocket client with async event loop in background thread. `connect()`, `send()`, `receive()`, `has_messages()`, `close()`

### Client (app.py)

- **App** — Main controller. Loads all game data at startup. `SERVER_URL = "wss://cegoemtiroteio.com.br/champion/ws"`.
- **Main menu:** Play Online, Local Match vs AI, Options, Quit
- **Screens:** `_select_fighter_screen()`, `_select_techniques_screen()`, `_select_items_screen()`, `_declare_actions_screen()`
- **Combat:** `_run_combat_volley()` — resolves exchanges with technique lookups, pauses between exchanges via `_wait_for_continue()` (Enter/Space/R to repeat/Escape/Alt+F4)
- **Online:** `_on_play_online()` — full match flow via WebSocket: connect, set name, join queue, wait for opponent, fighter/technique/item select, combat volleys, round/match results

### Server (`server/`)

Deployed at `https://cegoemtiroteio.com.br/champion/` on Ubuntu 24 VPS with nginx reverse proxy + uvicorn systemd service.

- **server/main.py** — FastAPI app with `/health` endpoint and `/ws` WebSocket endpoint; loads `GameData` at startup
- **server/game_data.py** — `GameData` registry: loads fighters, techniques, items, and feats once for server-side combat
- **server/session.py** — `PlayerSession` dataclass, `SessionManager` class
- **server/match_manager.py** — `MatchManager`: lobby queue, player pairing, match lifecycle, `ServerMatch` dataclass. Builds the `MatchState` (buffs + reactions) once both players finish item selection; resets rounds when both players ready up
- **server/combat_resolver.py** — `resolve_volley_server(match, techniques)`: authoritative combat resolution with full local-play parity (validated techniques, item buffs, Feats, item reactives, burn ticks, cheat-death, low-health)
- **server/client_handler.py** — `handle_message()`: dispatches incoming WebSocket messages to handlers; pushes `match_found` (with team) and `volley_result` to both players

### Data files (`game/data/`)

- **12 fighters:** each a combination of two internal archetypes (Strong/Agile/Smart/Sturdy → Power/Speed/Intellect/Health); attribute spread 6/5/3-3-or-4-2 summing to 17. Archetypes are internal only and never surfaced in-game.
- **53 techniques:** 41 shared plus 12 unique exclusives (one per fighter). Each fighter's pool is 6 shared + 1 exclusive = 7. Descriptions include mechanical effects after `|` separator.
- **47 items:** across 11 body slots. Descriptions include passive buffs and reactive triggers after `|` separator.
- **12 feats:** one innate passive per fighter, in `game/data/feats/`, referenced by each fighter's `feat_id`.

## Combat System

**6 base actions:** Strike, Block, Feint, Counter, Charge, Avoid — full 36-pair interaction matrix in `resolve_exchange()`.

**Volleys:** Each player secretly declares 3 actions, then exchanges resolve simultaneously in speed order (faster fighter acts first each exchange).

**Techniques:** Modified versions of base actions with damage modifiers, debuffs (weakened, slowed, vulnerable, predictable), healing, repositioning, advantage changes, item stealing/switching. Each use increases predictability, making future actions easier to counter.

**Items:** Passive buffs (health, power, speed, damage reduction, debuff resistance) and reactive triggers (when struck, when hit by technique, when dodge succeeds, when at low health).

**Positioning:** Verbal only — close/medium/far range, neutral/offensive/defensive advantage. No grid.

**Match flow:** Fighter select (each fighter's Feat is innate — no selection step) → pick base_intellect techniques (2–6) from a pool of 7 → equip up to base_speed items from a 7-slot panoply → best of 3 rounds → winner

## Key Conventions

- **Screen reader:** All UI feedback via `sr.speak()`. Always interrupt for new speech, don't interrupt for queued info.
- **Exchange pausing:** After each exchange, `_wait_for_continue()` pauses for Enter/Space/Escape/gamepad A. Press R to repeat the last announcement.
- **Alt+F4:** Closes the app from any screen. Checked in `_wait_for_continue()` via `is_key_pressed(K_F4) + is_modifier_held(KMOD_ALT)`.
- **Key detection:** Check `is_key_pressed()` BEFORE `controls.update()` — update transitions PRESSED → HELD.
- **Hotkey labels:** Ampersand (`&`) prefix in UI labels defines Alt-key shortcuts.
- **Sound files:** Referenced by name without extension. Both `.ogg` and `.wav` supported.
- **Gamepad constants:** Xbox-style mapping on `GameControls` (e.g., `GAMEPAD_A = 0`).
- **Windows DLLs** (OpenAL64.dll, SAAPI64.dll, nvdaControllerClient64.dll) for audio and screen reader.
- **2v2 forward compatibility:** `team_a`/`team_b` are lists, every action has `target_id`, turn order uses speed sorting.
- **Slot taxonomy:** HEAD, EYES, NECK, SHOULDERS, ARMS, CLOTHING, ARMOR, HANDS (enum-only, unused), RING, WAIST, FEET — 11 body slots. Each fighter's panoply covers 7 slots, with RING holding up to 2 items for hand-agnostic equipping.

## Deferred Follow-Ups

The seven follow-ups from the Feats/reactive-engine review (server parity, burn contract, Berserker Vest cap, low-health threshold, defense-success test coverage, structured `ExchangeResult` fields, doc nit) are all resolved, as are the three later local/online parity + match-lifecycle items (server match cleanup & disconnect notification, local side-effect application, shared action-matched technique guard). See `docs/FOLLOWUPS.md` for the resolution records and any newly deferred work.
