# Graph Report - .  (2026-07-21)

## Corpus Check
- 151 files · ~73,776 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1284 nodes · 2266 edges · 70 communities (43 shown, 27 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 101 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Game Match & Enums|Game Match & Enums]]
- [[_COMMUNITY_App Controller & AI|App Controller & AI]]
- [[_COMMUNITY_AudioForm Types & Errors|AudioForm Types & Errors]]
- [[_COMMUNITY_OpenAL Player|OpenAL Player]]
- [[_COMMUNITY_Screen Reader Core|Screen Reader Core]]
- [[_COMMUNITY_OpenAL Reverb|OpenAL Reverb]]
- [[_COMMUNITY_AudioForm Text Input|AudioForm Text Input]]
- [[_COMMUNITY_GameControls|GameControls]]
- [[_COMMUNITY_AudioForm High-Level API|AudioForm High-Level API]]
- [[_COMMUNITY_Server Client Handler|Server Client Handler]]
- [[_COMMUNITY_Combat Engine|Combat Engine]]
- [[_COMMUNITY_Champion Design Concepts|Champion Design Concepts]]
- [[_COMMUNITY_Menu System|Menu System]]
- [[_COMMUNITY_AudioForm Control Creation|AudioForm Control Creation]]
- [[_COMMUNITY_Combat Resolution & Tests|Combat Resolution & Tests]]
- [[_COMMUNITY_AudioForm List Operations|AudioForm List Operations]]
- [[_COMMUNITY_AudioForm State Queries|AudioForm State Queries]]
- [[_COMMUNITY_AudioForm Input Handling|AudioForm Input Handling]]
- [[_COMMUNITY_DJ Sound Manager|DJ Sound Manager]]
- [[_COMMUNITY_Match State Machine|Match State Machine]]
- [[_COMMUNITY_Fighter Data Model|Fighter Data Model]]
- [[_COMMUNITY_Technique Data Model|Technique Data Model]]
- [[_COMMUNITY_Item Data Model|Item Data Model]]
- [[_COMMUNITY_Server Session & Main|Server Session & Main]]
- [[_COMMUNITY_Client Networking|Client Networking]]
- [[_COMMUNITY_AI Opponent|AI Opponent]]
- [[_COMMUNITY_Integration Tests|Integration Tests]]
- [[_COMMUNITY_Game Data JSON|Game Data JSON]]
- [[_COMMUNITY_Menu Navigation|Menu Navigation]]
- [[_COMMUNITY_AudioForm Progress Bars|AudioForm Progress Bars]]
- [[_COMMUNITY_Controls Mouse & Gamepad|Controls Mouse & Gamepad]]
- [[_COMMUNITY_AudioForm Clipboard|AudioForm Clipboard]]
- [[_COMMUNITY_AudioForm Announcements|AudioForm Announcements]]
- [[_COMMUNITY_Server Match Manager|Server Match Manager]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]

## God Nodes (most connected - your core abstractions)
1. `AudioForm` - 88 edges
2. `GameControls` - 81 edges
3. `Player` - 60 edges
4. `DJ` - 52 edges
5. `EAXreverb` - 50 edges
6. `Menu` - 46 edges
7. `Control` - 38 edges
8. `App` - 37 edges
9. `FighterInstance` - 35 edges
10. `resolve_exchange()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `App` --uses--> `GameControls`  [INFERRED]
  app.py → controls.py
- `App` --uses--> `DJ`  [INFERRED]
  app.py → dj.py
- `App` --uses--> `FighterInstance`  [INFERRED]
  app.py → game/combat.py
- `App` --uses--> `ActionType`  [INFERRED]
  app.py → game/enums.py
- `App` --uses--> `MatchPhase`  [INFERRED]
  app.py → game/enums.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Champion Server Stack** — player_session_concept, session_manager_concept, client_handler_concept, match_manager_concept, server_match_concept, combat_resolver_concept, fastapi_server_concept [EXTRACTED 1.00]
- **Combat Resolution Pipeline (Techniques, Speed, Volleys)** — combat_resolver_concept, technique_wiring_rationale, effective_speed_rationale, match_manager_concept, champion_main_menu_concept, integration_test_concept [EXTRACTED 1.00]
- **Client-Server Networking Flow** — game_client_concept, fastapi_server_concept, client_handler_concept, session_manager_concept, match_manager_concept [EXTRACTED 1.00]
- **Combat Resolution Core** — docs_superpowers_specs_2026_07_21_champion_mvp_design_interaction_matrix, docs_superpowers_specs_2026_07_21_champion_mvp_design_positioning_system, docs_superpowers_specs_2026_07_21_champion_mvp_design_technique_modifier_system, docs_superpowers_specs_2026_07_21_champion_mvp_design_item_buff_system, superpowers_sdd_task_7_brief_combat_engine_module [INFERRED 0.95]
- **Game Data Layer** — superpowers_sdd_task_2_brief_shared_enums_module, superpowers_sdd_task_3_brief_fighter_data_module, superpowers_sdd_task_4_brief_technique_data_module, superpowers_sdd_task_5_brief_item_data_module, superpowers_sdd_task_6_brief_json_data_files [INFERRED 0.95]
- **Match Lifecycle and Phase Flow** — docs_superpowers_specs_2026_07_21_champion_mvp_design_match_phase_flow, superpowers_sdd_task_8_brief_match_state_machine_module, superpowers_sdd_task_9_brief_ai_opponent_module, docs_superpowers_specs_2026_07_21_champion_mvp_design_volley_combat_system [INFERRED 0.85]

## Communities (70 total, 27 thin omitted)

### Community 0 - "Game Match & Enums"
Cohesion: 0.07
Nodes (49): Start a local match against AI., MatchPhase, Phases of a match from lobby to conclusion., advance_phase(), all_actions_declared(), apply_round_result(), check_match_end(), check_round_end() (+41 more)

### Community 1 - "App Controller & AI"
Cohesion: 0.08
Nodes (52): app.py - Champion Application Controller =======================================, Run one volley (3 actions) of combat for local play., choose_ai_actions(), choose_ai_fighter(), choose_ai_items(), choose_ai_techniques(), game/ai.py - AI opponent for Champion ====================================== Pro, Pick a fighter ID from the available roster. (+44 more)

### Community 2 - "AudioForm Types & Errors"
Cohesion: 0.07
Nodes (21): ControlType, EditMode, FormError, Text entry speech flags for input boxes., Text edit modes for programmatic text modification., Types of form controls., Error codes returned by form operations., TextFlag (+13 more)

### Community 4 - "Screen Reader Core"
Cohesion: 0.06
Nodes (36): Exception, braille(), _cleanup(), _ensure_ready(), get_active_screen_reader(), has_braille(), has_speech(), initialize() (+28 more)

### Community 6 - "AudioForm Text Input"
Cohesion: 0.09
Nodes (23): Control, Speak text via screen reader., Handle input for text input controls., Internal class representing a form control., Get the display character (handles password mask)., Convert a character to its spoken representation., Add a character at the cursor position., Replace character at cursor position (overwrite mode). (+15 more)

### Community 7 - "GameControls"
Cohesion: 0.05
Nodes (23): GameControls, Manages all input devices for audiogame development.          Provides a unified, Check if a key was just pressed this frame., Check if a key is currently held down., Check if a key was just released this frame., Get current modifier key state (KMOD_* flags)., Get current mouse position., Get mouse wheel scroll this frame (x, y). (+15 more)

### Community 8 - "AudioForm High-Level API"
Cohesion: 0.06
Nodes (23): AudioForm, Check if a control is enabled., Get the last error code., Validate a control index., Audio-based form system for accessible audiogame interfaces.          Provides a, Initialize the audio form system.                  Args:             dj: Optiona, Check if a quit/close event was received., Reset the form to its initial state. (+15 more)

### Community 9 - "Server Client Handler"
Cohesion: 0.07
Nodes (33): _handle_declare_actions(), _handle_join_queue(), handle_message(), _handle_ready_next_round(), _handle_select_fighter(), _handle_select_items(), _handle_select_techniques(), _handle_set_name() (+25 more)

### Community 10 - "Combat Engine"
Cohesion: 0.10
Nodes (36): Enum, apply_buffs(), compute_damage(), ExchangeResult, game/combat.py - Combat engine for Champion ====================================, Outcome of a single action exchange between two fighters., Compute base damage from power and advantage., Apply passive buffs from selected items to a fighter instance. (+28 more)

### Community 11 - "Champion Design Concepts"
Cohesion: 0.08
Nodes (38): Champion Main Menu and AI Match Flow, Champion Project Identity and Branding, handle_message WebSocket Dispatch, resolve_volley_server Function, Server Uses get_effective_speed() for Turn Order, Champion FastAPI Game Server, GameClient WebSocket Class, Game Data Loading (Fighters, Techniques, Items) (+30 more)

### Community 12 - "Menu System"
Cohesion: 0.10
Nodes (19): Menu, Convenience function to construct and run a Menu.      The options list may comp, Implements a flexible audio menu system with accessibility features.          Me, Play the movement sound effect if configured., Play the cancel/back sound effect if configured., Play the boundary sound effect if configured., Play the wrap sound effect if configured, falling back to move SFX., Announce the current menu item. (+11 more)

### Community 13 - "AudioForm Control Creation"
Cohesion: 0.07
Nodes (18): input_box(), message_box(), Extract hotkey from caption (letter after &)., Convert a letter to pygame key constant., Internal method to set button attributes., Display a simple message box dialog. Returns index of pressed button., Display a simple input dialog. Returns entered text or None if cancelled., Create and announce the form window. (+10 more)

### Community 14 - "Combat Resolution & Tests"
Cohesion: 0.09
Nodes (32): get_effective_power(), Resolve a single action exchange between two fighters., Get power after buffs and debuffs., resolve_exchange(), make_test_fighter(), Counter should lose to Block., Technique damage modifier should increase damage., Faster fighter should take less damage in a clash. (+24 more)

### Community 16 - "AudioForm State Queries"
Cohesion: 0.12
Nodes (26): _dict_to_item(), ItemBuff, ItemData, ItemReactive, load_all_items(), load_item(), game/item.py - Item data model for Champion ====================================, A passive stat modification from an item. (+18 more)

### Community 18 - "DJ Sound Manager"
Cohesion: 0.11
Nodes (14): Process a pygame event and update input states.                  Args:, Handle keyboard key press., Handle keyboard key release., Handle mouse button press., Handle mouse button release., Handle mouse movement., Handle mouse wheel scroll., Handle gamepad button press. (+6 more)

### Community 19 - "Match State Machine"
Cohesion: 0.12
Nodes (12): Poll the client for a specific message type, with timeout in seconds., Show fighter selection menu. Returns FighterData or None., Show technique selection screen. Returns list of 3 technique IDs or None., Show item selection screen. Returns list of 2 item IDs or None., Screen for declaring 3 actions for a volley., Announce the result of one exchange. Returns the spoken text for repeat., Announce round result., Announce match result. (+4 more)

### Community 21 - "Technique Data Model"
Cohesion: 0.15
Nodes (5): App, Wait for the player to press Enter, Space, or R before continuing.          Args, main(), main.py - Champion Entry Point =============================== Main entry point, Initialize pygame and run the application.

### Community 22 - "Item Data Model"
Cohesion: 0.11
Nodes (9): GameClient, game/network.py - Client-side WebSocket connection =============================, WebSocket client for connecting to the Champion server., Connect to the server. Runs the event loop in a background thread., Receive messages from server and queue them., Send a message to the server., Get the next queued message from the server, or None., Check if there are queued messages. (+1 more)

### Community 23 - "Server Session & Main"
Cohesion: 0.15
Nodes (8): object, c_void, Compressor, lib_alc, lib_efx, lib_openal, LoadSound, Structure

### Community 24 - "Client Networking"
Cohesion: 0.14
Nodes (8): Process input events and update form state.                  Call this method on, Check if a key is currently held down., Check if a key was just pressed this frame., Navigate to the next visible control., Navigate to the previous visible control., Check for Alt+hotkey combinations., Process input for the focused control., Get the index of the currently focused control.

### Community 25 - "AI Opponent"
Cohesion: 0.12
Nodes (11): InputState, InputType, controls.py - Game Controls Input Management ===================================, Types of input devices., State of an input (key, button, etc.)., MenuBindings, menu.py - Accessible Audio Menu System ======================================= A, Defines input bindings for menu navigation.          Each binding is a tuple of (+3 more)

### Community 26 - "Integration Tests"
Cohesion: 0.27
Nodes (16): pytest Unit Test Suite, Burning Wheel Gold Design Inspiration, Action Interaction Matrix, Item Buff and Reactive System, Match Phase Flow, Combat Positioning System, Technique Modifier System, Volley-of-3 Combat System (+8 more)

### Community 30 - "Controls Mouse & Gamepad"
Cohesion: 0.15
Nodes (9): list_box(), ListItem, audio_form.py - Audio Form System for Audiogames ===============================, Represents an item in a list control., Display a list selection dialog. Returns selected index(es) or None., Add an item to a list control., Get the current selection position in a list., Set the current selection position in a list. (+1 more)

### Community 31 - "AudioForm Clipboard"
Cohesion: 0.14
Nodes (8): GamepadState, Check if button is currently held down., Check if button was just released this frame., Get all connected gamepads., Get gamepad axis value (-1.0 to 1.0) with deadzone applied., Stores the current state of a gamepad., Get axis value with deadzone applied., Check if button was just pressed this frame.

### Community 32 - "AudioForm Announcements"
Cohesion: 0.14
Nodes (7): Check if mouse button was just released this frame., Check if a mouse button was just released this frame., Get a gamepad by instance ID.                  If instance_id is 0 and no gamepa, Check if a gamepad button was just released this frame., Get gamepad hat/d-pad value as (x, y)., Vibrate/rumble a gamepad.                  Args:             low_frequency: Inte, Check if a gamepad is currently vibrating.

### Community 33 - "Server Match Manager"
Cohesion: 0.20
Nodes (7): Announcer, Provides a unified mechanism to announce menu text and play sound effects     vi, Play a wav file using DJ if possible., Announce a label, optionally including positional information., Announce immediately, optionally adding position and choosing between audio and, Announce a hint if provided., Stop all currently playing speech and sound effects.

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (7): Any, Toggle a checkbox type item., Adjust a slider type item by delta steps., Set this radio item as selected and clear others in the same group., Play the selection sound effect if configured., Handle the activation of the current item and return a structured result., Adjust the current item if it is a checkbox, radio, or slider.

### Community 37 - "Community 37"
Cohesion: 0.23
Nodes (6): Play a named SFX via DJ if both DJ and the SFX name are set., Announce the current list item including checked state., Move list selection by direction (+1/-1) with wrap/boundary/normal SFX., Jump to first or last list item with move/boundary SFX., Type-ahead search for list controls., Handle input for list controls.

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (7): MouseState, Stores the current state of the mouse., Check if mouse button was just pressed this frame., Initialize the controls manager.                  Args:             enable_speec, Detect and initialize all connected gamepads., Check if a mouse button was just pressed this frame., Check if a gamepad button was just pressed this frame.

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (12): load_all_fighters(), Load all fighter JSON files from a directory. Returns dict keyed by fighter id., load_all_fighters should load all JSON files from a directory., test_load_all_fighters(), All game data should load without errors., Every action pair should produce a valid outcome., All fighter technique references should resolve to actual technique files., All fighter item references should resolve to actual item files. (+4 more)

### Community 45 - "Community 45"
Cohesion: 0.25
Nodes (4): Get direction from axis value (-1, 0, or 1).                  Returns:, Get d-pad direction as (horizontal, vertical)., Check if an input should trigger based on repeat timing.                  Handle, Process gamepad analog stick and d-pad for navigation.                  Returns:

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (4): Internal method to set focus., Announce a control when it receives focus., Get the spoken name for this control type., Set focus to a specific control.

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (7): Test-Driven Development Approach, Champion Project, Screen Reader Accessibility Constraint, Server-Authoritative Architecture, JSON-over-WebSocket Communication Protocol, Server Runtime Dependencies, VPS Server Deployment Configuration

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (6): get_effective_speed(), Get speed after buffs and debuffs., server/combat_resolver.py - Server-side combat resolution ======================, Resolve a full volley (3 exchanges) for a match.      Returns a volley_result me, # TODO: Load technique data on the server and pass real TechniqueData objects., resolve_volley_server()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (3): Update progress bar automatic speech timers., Speak the current progress value., Set the progress bar value (0-100).

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (3): Add a gamepad by device index., Remove a disconnected gamepad., Speak text via screen reader if enabled.

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (3): Check if mouse button is currently held down., Check if a mouse button is currently held down., Check if a gamepad button is currently held down.

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (3): Update input states at the end of each frame.                  Call this once pe, Stop vibration on a gamepad immediately.                  Args:             game, Internal method to stop vibration.

## Knowledge Gaps
- **11 isolated node(s):** `Task 10 Report: Server Scaffolding`, `Task 11 Report: Server Client Handler`, `Task 12 Report: Server Match Manager`, `Task 13 Report: Server Combat Resolver`, `Task 14 Report: Server Main Entry Point` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DJ` connect `AudioForm Types & Errors` to `App Controller & AI`, `Server Match Manager`, `AudioForm Text Input`, `AudioForm High-Level API`, `Menu System`, `Match State Machine`, `Technique Data Model`, `AI Opponent`, `Controls Mouse & Gamepad`?**
  _High betweenness centrality (0.464) - this node is a cross-community bridge._
- **Why does `GameControls` connect `GameControls` to `App Controller & AI`, `AudioForm Types & Errors`, `AudioForm Text Input`, `AudioForm High-Level API`, `Menu System`, `DJ Sound Manager`, `Match State Machine`, `Technique Data Model`, `AI Opponent`, `Controls Mouse & Gamepad`, `AudioForm Clipboard`, `AudioForm Announcements`, `Server Match Manager`, `Community 38`, `Community 54`, `Community 55`, `Community 56`, `Community 59`, `Community 60`, `Community 61`, `Community 62`, `Community 63`, `Community 64`?**
  _High betweenness centrality (0.234) - this node is a cross-community bridge._
- **Why does `AudioForm` connect `AudioForm High-Level API` to `AudioForm Types & Errors`, `Community 37`, `AudioForm Text Input`, `GameControls`, `AudioForm Control Creation`, `Community 46`, `Community 53`, `Client Networking`, `Controls Mouse & Gamepad`?**
  _High betweenness centrality (0.217) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `AudioForm` (e.g. with `GameControls` and `DJ`) actually correct?**
  _`AudioForm` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `GameControls` (e.g. with `App` and `AudioForm`) actually correct?**
  _`GameControls` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `DJ` (e.g. with `App` and `AudioForm`) actually correct?**
  _`DJ` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `app.py - Champion Application Controller =======================================`, `Connect to the game server and play an online match.`, `Start a local match against AI.` to the rest of the system?**
  _400 weakly-connected nodes found - possible documentation gaps or missing edges._