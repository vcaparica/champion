# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python audiogame development framework/template built on Pygame. Designed for building accessible games for blind/visually impaired players with screen reader integration, spatial audio, and gamepad support.

## Running

```bash
python main.py
```

Dependencies: `pygame`, `cytolk` (required); `pyogg` (OGG audio, falls back to WAV), `pyperclip` (clipboard in forms) are optional. No requirements.txt exists — install manually via pip.

No build system, test framework, or linter is configured. This is a standalone template meant to be copied and extended.

## Architecture

**Entry flow:** `main.py` → `App` (app.py) → `App.main_menu()` → game loop

**Core components:**

- **App** (app.py) — Main controller. Initializes the window, audio, controls, and screen reader. Manages the main menu and application lifecycle.
- **Menu / MenuItem** (menu.py) — Accessible menu system with keyboard/gamepad navigation, type-ahead search, item wrapping, checkboxes, radio buttons, and sliders. `Menu.run()` enters a blocking loop and returns the selected item result.
- **AudioForm** (audio_form.py) — Dialog/form system with buttons, input boxes, lists, checkboxes, and progress bars. Controls are created via `create_button()`, `create_input_box()`, etc. The form runs via a `monitor()` loop.
- **GameControls** (controls.py) — Unified input handling for keyboard, mouse, and gamepad. Uses an `InputState` enum (RELEASED → PRESSED → HELD → JUST_RELEASED) with per-frame `update()` calls to transition states. Query with `is_key_pressed()`, `is_gamepad_button_pressed()`, etc.
- **DJ** (dj.py) — Sound manager for SFX and BGM. Loads all files from `snd/sfx/` and `snd/bgm/` folders. Supports 3D panning via `play_sfx(name, x=position)`. Uses OpenAL under the hood.
- **sr** (sr.py) — Screen reader speech abstraction via Tolk/cytolk. Key functions: `speak(text, interrupt=True/False)`, `silence()`, `braille()`. Auto-detects NVDA, JAWS, or SAPI fallback.
- **openal.py** — Low-level OpenAL C++ binding wrapper (from pyglet). Not typically modified directly.

**Data flow:** Pygame events → `GameControls.process_event()` → state queries by Menu/AudioForm → speech output via `sr.speak()` + audio via `DJ`

## Key Conventions

- **Hotkey labels:** Ampersand (`&`) prefix in UI labels defines Alt-key shortcuts (e.g., `"&OK"` → Alt+O).
- **Sound files:** Referenced by name without extension. Both `.ogg` and `.wav` supported; OGG preferred.
- **Game loop timing:** `pygame.time.delay(10)` for ~100 FPS loops.
- **Gamepad constants:** Xbox-style mapping on `GameControls` class (e.g., `GAMEPAD_A = 0`, `GAMEPAD_B = 1`).
- **Windows DLLs** (OpenAL64.dll, SAAPI64.dll, nvdaControllerClient64.dll) are included for audio and screen reader integration on Windows.
