# Fighter Selection Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rich 2D-navigable fighter selection screen where left/right switches fighters and up/down browses detailed fighter information sections.

**Architecture:** New `FighterSelectScreen` class in `game/fighter_select.py` encapsulates the full 2D navigation, speech output, and input handling. It follows the same dependency-injection pattern as `Menu` (external DJ, GameControls). App.py replaces the body of `_select_fighter_screen()` to delegate to this class.

**Tech Stack:** Python 3, Pygame for input/clock, sr.speak for TTS, DJ for SFX, GameControls for unified input. No new dependencies.

## Global Constraints

- All speech via `sr.speak(text, interrupt=True)` for immediate feedback
- Check `controls.is_key_pressed()` BEFORE `controls.update()` — update transitions PRESSED→HELD
- Alt+F4 detected with `is_key_pressed(K_F4) + is_modifier_held(KMOD_ALT)`, sets app quit flag
- Left/right always switches fighters across all sections, resets section to top
- Gamepad constants on GameControls class (GAMEPAD_A=0, GAMEPAD_B=1, GAMEPAD_X=2, etc.)
- SFX names passed as strings, played via `dj.play_sfx(name)`

---

### Task 1: Create FighterSelectScreen class skeleton

**Files:**
- Create: `game/fighter_select.py`

**Interfaces:**
- Produces: `FighterSelectScreen.__init__(fighters, techniques, items, dj, controls, sfx_move, sfx_select, sfx_cancel)`, `FighterSelectScreen.run() -> Optional[FighterData]`, `FighterSelectScreen.quit_requested -> bool`

- [ ] **Step 1: Create the file with imports, constants, and __init__**

```python
"""
game/fighter_select.py - Fighter Selection Screen for Champion
===============================================================
A 2D-navigable fighter selection screen. Left/right switches between
fighters, up/down browses information sections for the selected fighter.
"""
import pygame
from typing import Optional

from sr import speak
from game.fighter import FighterData


class FighterSelectScreen:
    """2D fighter selection screen with detailed information browsing."""

    # Info section indices
    SECTION_NAME_DESC = 0
    SECTION_STATS = 1
    SECTION_TECHNIQUES = 2
    SECTION_EQUIPMENT = 3
    SECTION_SELECT = 4
    SECTION_COUNT = 5

    # Gamepad button indices (Xbox-style)
    _GP_A = 0
    _GP_B = 1
    _GP_X = 2
    _GP_Y = 3

    # Axis threshold for analog stick navigation
    _AXIS_THRESHOLD = 0.5

    def __init__(
        self,
        fighters: dict[str, FighterData],
        techniques: dict,
        items: dict,
        dj,
        controls,
        sfx_move: Optional[str] = None,
        sfx_select: Optional[str] = None,
        sfx_cancel: Optional[str] = None,
    ) -> None:
        self._fighters = fighters
        self._techniques = techniques
        self._items = items
        self._dj = dj
        self._controls = controls
        self._sfx_move = sfx_move
        self._sfx_select = sfx_select
        self._sfx_cancel = sfx_cancel

        self._fighter_list = list(fighters.values())
        self._fighter_index = 0
        self._section_index = 0
        self._quit_requested = False

    @property
    def quit_requested(self) -> bool:
        """True if Alt+F4 was pressed during the screen."""
        return self._quit_requested
```

- [ ] **Step 2: Commit**

```bash
git add game/fighter_select.py
git commit -m "feat: add FighterSelectScreen class skeleton"
```

---

### Task 2: Implement fighter navigation

**Files:**
- Modify: `game/fighter_select.py` (add methods)

**Interfaces:**
- Consumes: `__init__` from Task 1
- Produces: `_current_fighter() -> FighterData`, `_move_fighter(direction: int) -> None`, `_announce_fighter() -> None`

- [ ] **Step 1: Add fighter accessor, announcer, and movement methods**

Add these methods inside the class (after `quit_requested`):

```python
    def _current_fighter(self) -> FighterData:
        """Return the currently selected fighter."""
        return self._fighter_list[self._fighter_index]

    def _announce_fighter(self) -> None:
        """Speak the current fighter's name."""
        fighter = self._current_fighter()
        speak(fighter.name, True)

    def _move_fighter(self, direction: int) -> None:
        """Move fighter selection by +1 or -1. Wraps around. Resets section to top."""
        count = len(self._fighter_list)
        self._fighter_index = (self._fighter_index + direction) % count
        self._section_index = 0
        self._play_sfx(self._sfx_move)
        self._announce_fighter()
        self._announce_section()
```

- [ ] **Step 2: Commit**

```bash
git add game/fighter_select.py
git commit -m "feat: add fighter navigation methods to FighterSelectScreen"
```

---

### Task 3: Implement section navigation

**Files:**
- Modify: `game/fighter_select.py` (add method)

**Interfaces:**
- Consumes: `_move_fighter` from Task 2
- Produces: `_move_section(direction: int) -> None`

- [ ] **Step 1: Add section movement method**

Add this method inside the class:

```python
    def _move_section(self, direction: int) -> None:
        """Move section selection by +1 or -1. Wraps around."""
        self._section_index = (self._section_index + direction) % self.SECTION_COUNT
        self._play_sfx(self._sfx_move)
        self._announce_section()
```

- [ ] **Step 2: Commit**

```bash
git add game/fighter_select.py
git commit -m "feat: add section navigation method to FighterSelectScreen"
```

---

### Task 4: Implement section content announcement

**Files:**
- Modify: `game/fighter_select.py` (add `_announce_section` and helper)

**Interfaces:**
- Consumes: `_current_fighter()` from Task 2, `SECTION_*` constants from Task 1
- Produces: `_announce_section() -> None`

- [ ] **Step 1: Add the SFX helper and full section announcement**

Add these methods inside the class:

```python
    def _play_sfx(self, sfx_name: Optional[str]) -> None:
        """Play a named SFX if configured."""
        if sfx_name is not None:
            try:
                self._dj.play_sfx(sfx_name)
            except Exception:
                pass

    def _announce_section(self) -> None:
        """Speak the current section's content for the current fighter."""
        fighter = self._current_fighter()

        if self._section_index == self.SECTION_NAME_DESC:
            self._speak_name_and_description(fighter)

        elif self._section_index == self.SECTION_STATS:
            self._speak_stats(fighter)

        elif self._section_index == self.SECTION_TECHNIQUES:
            self._speak_techniques(fighter)

        elif self._section_index == self.SECTION_EQUIPMENT:
            self._speak_equipment(fighter)

        elif self._section_index == self.SECTION_SELECT:
            speak(f"Press Enter to select {fighter.name}.", True)

    def _speak_name_and_description(self, fighter: FighterData) -> None:
        """Speak the fighter's name and full description."""
        speak(fighter.name, True)
        speak(fighter.description, False)

    def _speak_stats(self, fighter: FighterData) -> None:
        """Speak the fighter's base stats."""
        speak(
            f"Health {fighter.base_health}. "
            f"Speed {fighter.base_speed}. "
            f"Power {fighter.base_power}.",
            True
        )

    def _speak_techniques(self, fighter: FighterData) -> None:
        """Speak all available techniques for the current fighter."""
        found = 0
        parts = []
        for tid in fighter.technique_ids:
            tech = self._techniques.get(tid)
            if tech is not None:
                parts.append(f"{tech.name}: {tech.description}")
                found += 1
        if found == 0:
            speak("No techniques available.", True)
        else:
            speak(f"{found} techniques. " + " ".join(parts), True)

    def _speak_equipment(self, fighter: FighterData) -> None:
        """Speak all available items organized by body slot."""
        found = 0
        parts = []
        for slot, item_ids in fighter.panoply.items():
            for iid in item_ids:
                item = self._items.get(iid)
                if item is not None:
                    parts.append(f"{slot.value}: {item.name}: {item.description}")
                    found += 1
        if found == 0:
            speak("No equipment available.", True)
        else:
            speak(f"{found} items. " + " ".join(parts), True)
```

- [ ] **Step 2: Commit**

```bash
git add game/fighter_select.py
git commit -m "feat: add section content announcement to FighterSelectScreen"
```

---

### Task 5: Implement main loop with keyboard input

**Files:**
- Modify: `game/fighter_select.py` (add `run()` method and helper)

**Interfaces:**
- Consumes: all navigation and announcement methods from Tasks 2-4
- Produces: `run() -> Optional[FighterData]`

- [ ] **Step 1: Add helper and run() method**

Add these methods inside the class:

```python
    def _is_bound_key_pressed(self, *keys) -> bool:
        """Check if any of the given pygame key constants was just pressed."""
        for key in keys:
            if self._controls.is_key_pressed(key):
                return True
        return False

    def _is_bound_button_pressed(self, *buttons) -> bool:
        """Check if any of the given gamepad button indices was just pressed."""
        for button in buttons:
            if self._controls.is_gamepad_button_pressed(button):
                return True
        return False

    def run(self) -> Optional[FighterData]:
        """Run the fighter selection screen.

        Returns:
            FighterData if a fighter was selected, None if cancelled or quit.
            Check quit_requested property to distinguish cancel from Alt+F4.
        """
        if not self._fighter_list:
            speak("No fighters available.", True)
            return None

        self._fighter_index = 0
        self._section_index = 0
        self._quit_requested = False

        # Announce initial state
        self._announce_fighter()
        self._announce_section()

        clock = pygame.time.Clock()

        while True:
            # Process pygame events (needed for QUIT detection)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit_requested = True
                    self._play_sfx(self._sfx_cancel)
                    return None
                self._controls.process_event(event)

            # --- Check keys BEFORE controls.update() ---
            # update() transitions PRESSED->HELD, so we check first.

            # Alt+F4: quit the entire app
            alt_f4 = (
                self._controls.is_key_pressed(pygame.K_F4)
                and self._controls.is_modifier_held(pygame.KMOD_ALT)
            )
            if alt_f4:
                self._quit_requested = True
                self._play_sfx(self._sfx_cancel)
                return None

            # Cancel / back
            if self._is_bound_key_pressed(pygame.K_ESCAPE) or self._is_bound_button_pressed(self._GP_B):
                self._play_sfx(self._sfx_cancel)
                return None

            # Fighter navigation (left/right)
            if self._is_bound_key_pressed(pygame.K_LEFT):
                self._move_fighter(-1)
            elif self._is_bound_key_pressed(pygame.K_RIGHT):
                self._move_fighter(1)

            # Section navigation (up/down)
            elif self._is_bound_key_pressed(pygame.K_UP):
                self._move_section(-1)
            elif self._is_bound_key_pressed(pygame.K_DOWN):
                self._move_section(1)

            # Select / confirm (only on the SELECT section)
            elif self._is_bound_key_pressed(pygame.K_RETURN, pygame.K_KP_ENTER) or self._is_bound_button_pressed(self._GP_A):
                if self._section_index == self.SECTION_SELECT:
                    self._play_sfx(self._sfx_select)
                    return self._current_fighter()

            # Repeat current section
            elif self._is_bound_key_pressed(pygame.K_SPACE) or self._is_bound_button_pressed(self._GP_X):
                self._announce_section()

            # Repeat fighter name
            elif self._is_bound_key_pressed(pygame.K_t):
                self._announce_fighter()

            # Help
            elif self._is_bound_key_pressed(pygame.K_h):
                self._speak_help()

            # --- Update controls state AFTER key checks ---
            self._controls.update()

            clock.tick(60)

    def _speak_help(self) -> None:
        """Speak available controls."""
        help_text = (
            "Left and right arrows to switch fighters. "
            "Up and down arrows to browse information. "
            "Enter to select the current fighter. "
            "Escape to go back. "
            "Space to repeat current information. "
            "T to repeat the fighter name. "
            "H for this help message."
        )
        speak(help_text, True)
```

- [ ] **Step 2: Run a quick syntax check**

```bash
python -c "from game.fighter_select import FighterSelectScreen; print('Import OK')"
```
Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add game/fighter_select.py
git commit -m "feat: add main loop with keyboard input to FighterSelectScreen"
```

---

### Task 6: Add gamepad D-pad and analog stick navigation

**Files:**
- Modify: `game/fighter_select.py` (extend `run()` gamepad handling)

**Interfaces:**
- Consumes: `run()` method from Task 5
- Produces: gamepad-aware navigation in `run()`

- [ ] **Step 1: Add GameControls import and d-pad/axis handling method**

Add this import at the top of the file (update the imports section):

```python
from controls import GameControls
```

Insert this method inside the class (before `run()`):

```python
    def _process_gamepad_navigation(self) -> Optional[tuple]:
        """Process gamepad d-pad and left stick for 2D navigation.

        Returns:
            ('fighter', direction) or ('section', direction) or None.
            direction is -1 (up/left) or 1 (down/right).
        """
        # D-pad
        hat_x, hat_y = self._controls.get_gamepad_hat(0)

        # Left analog stick
        stick_x = self._controls.get_gamepad_axis(GameControls.AXIS_LEFT_X)
        stick_y = self._controls.get_gamepad_axis(GameControls.AXIS_LEFT_Y)

        # Combine: d-pad takes priority
        horiz = hat_x if hat_x != 0 else (
            1 if stick_x > self._AXIS_THRESHOLD else (
                -1 if stick_x < -self._AXIS_THRESHOLD else 0
            )
        )
        vert = hat_y if hat_y != 0 else (
            -1 if stick_y < -self._AXIS_THRESHOLD else (
                1 if stick_y > self._AXIS_THRESHOLD else 0
            )
        )

        # Horizontal (fighter switch) takes priority over vertical
        if horiz != 0:
            return ('fighter', horiz)
        if vert != 0:
            return ('section', -vert)  # invert: stick up = negative, but we want up = -1

        return None
```

Now add gamepad navigation into `run()`. Insert this block right after the keyboard navigation elif chain (before the `self._controls.update()` call):

```python
            # --- Gamepad d-pad / analog stick navigation ---
            # Process only when no keyboard nav key was pressed this frame
            nav = self._process_gamepad_navigation()
            if nav is not None:
                axis, direction = nav
                if axis == 'fighter':
                    self._move_fighter(direction)
                elif axis == 'section':
                    self._move_section(direction)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from game.fighter_select import FighterSelectScreen; print('Import OK')"
```
Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add game/fighter_select.py
git commit -m "feat: add gamepad d-pad and analog stick navigation"
```

---

### Task 7: Integrate with app.py

**Files:**
- Modify: `app.py` (replace `_select_fighter_screen` body, lines 364-394)

**Interfaces:**
- Consumes: `FighterSelectScreen` from Tasks 1-6
- Produces: updated `_select_fighter_screen()` with same return contract

- [ ] **Step 1: Replace `_select_fighter_screen` method body**

Replace lines 364-394 of `app.py` (the existing `_select_fighter_screen` method):

```python
    def _select_fighter_screen(self) -> Optional[object]:
        """Show fighter selection screen. Returns FighterData or None."""
        from game.fighter_select import FighterSelectScreen

        screen = FighterSelectScreen(
            fighters=self.fighters,
            techniques=self.techniques,
            items=self.items,
            dj=self.dj,
            controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE,
            sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT,
        )
        fighter = screen.run()

        if screen.quit_requested:
            self._handle_quit()
            return None

        if fighter is None:
            return None

        speak(f"Selected {fighter.name}. {fighter.description}", False)
        return fighter
```

- [ ] **Step 2: Verify syntax**

```bash
python -c "from app import App; print('Import OK')"
```
Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: integrate FighterSelectScreen into app.py"
```

---

### Task 8: Write tests

**Files:**
- Create: `tests/test_fighter_select.py`

**Interfaces:**
- Consumes: `FighterSelectScreen` from Tasks 1-6, `FighterData` from game.fighter
- Produces: test coverage for the screen class

- [ ] **Step 1: Create test file with unit tests**

```python
"""Tests for FighterSelectScreen."""
import pygame
import pytest
from unittest.mock import MagicMock, patch
from game.fighter_select import FighterSelectScreen
from game.fighter import FighterData
from game.enums import BodySlot


def _make_fighter(fid="test", name="Test", health=50, speed=5, power=8):
    """Helper to create a minimal FighterData for tests."""
    return FighterData(
        id=fid,
        name=name,
        description="A test fighter.",
        base_health=health,
        base_speed=speed,
        base_power=power,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={},
    )


def _make_fighters_dict(*fighters):
    """Helper to create a fighters dict from FighterData instances."""
    return {f.id: f for f in fighters}


class TestFighterSelectScreenInit:
    """Tests for __init__ and properties."""

    def test_init_stores_fighters(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert len(screen._fighter_list) == 2
        assert screen._fighter_index == 0
        assert screen._section_index == 0

    def test_quit_requested_defaults_false(self):
        screen = FighterSelectScreen({}, {}, {}, None, None)
        assert screen.quit_requested is False

    def test_fighter_list_order_preserved(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        names = [f.name for f in screen._fighter_list]
        assert "Alpha" in names
        assert "Bravo" in names


class TestFighterSelectScreenNavigation:
    """Tests for navigation logic."""

    def test_move_fighter_right(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert screen._fighter_index == 0
        screen._move_fighter(1)
        assert screen._fighter_index == 1

    def test_move_fighter_wraps_left(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert screen._fighter_index == 0
        screen._move_fighter(-1)
        assert screen._fighter_index == 1

    def test_move_fighter_resets_section_to_top(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        screen._section_index = 3
        screen._move_fighter(1)
        assert screen._section_index == 0

    def test_move_section_down(self):
        screen = FighterSelectScreen({}, {}, {}, None, None)
        screen._section_index = 0
        screen._move_section(1)
        assert screen._section_index == 1

    def test_move_section_wraps_up(self):
        screen = FighterSelectScreen({}, {}, {}, None, None)
        screen._section_index = 0
        screen._move_section(-1)
        assert screen._section_index == FighterSelectScreen.SECTION_COUNT - 1

    def test_current_fighter(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert screen._current_fighter().name == "Alpha"


class TestFighterSelectScreenRun:
    """Tests for the run() method behavior."""

    def test_run_returns_none_when_no_fighters(self):
        screen = FighterSelectScreen({}, {}, {}, None, None)
        result = screen.run()
        assert result is None

    def test_run_returns_fighter_on_select(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()
        # Simulate: no quit, no cancel, then SELECT section with Enter
        mock_ctrl.is_key_pressed.side_effect = lambda k: k == pygame.K_RETURN
        mock_ctrl.is_modifier_held.return_value = False
        mock_ctrl.is_gamepad_button_pressed.return_value = False
        mock_ctrl.get_gamepad_hat.return_value = (0, 0)
        mock_ctrl.get_gamepad_axis.return_value = 0.0

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        # Set section to SELECT
        screen._section_index = FighterSelectScreen.SECTION_SELECT
        result = screen.run()
        assert result is not None
        assert result.name == "Alpha"

    def test_run_returns_none_on_escape(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()
        mock_ctrl.is_key_pressed.side_effect = lambda k: k == pygame.K_ESCAPE
        mock_ctrl.is_modifier_held.return_value = False
        mock_ctrl.is_gamepad_button_pressed.return_value = False

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        result = screen.run()
        assert result is None
        assert screen.quit_requested is False

    def test_run_sets_quit_requested_on_alt_f4(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()
        # Simulate Alt+F4: K_F4 pressed + Alt modifier held
        call_count = [0]

        def key_side_effect(k):
            call_count[0] += 1
            # First few frames: K_F4 is pressed (not other keys)
            if call_count[0] <= 2:
                return k == pygame.K_F4
            return False

        mock_ctrl.is_key_pressed.side_effect = key_side_effect
        mock_ctrl.is_modifier_held.return_value = True
        mock_ctrl.is_gamepad_button_pressed.return_value = False

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        result = screen.run()
        assert result is None
        assert screen.quit_requested is True

    def test_enter_does_nothing_outside_select_section(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()
        # First frames: Enter pressed but we're on section 0 (name/desc)
        # Later frames: Escape pressed to exit
        call_count = [0]

        def key_side_effect(k):
            call_count[0] += 1
            if call_count[0] <= 3:
                return k == pygame.K_RETURN
            return k == pygame.K_ESCAPE

        mock_ctrl.is_key_pressed.side_effect = key_side_effect
        mock_ctrl.is_modifier_held.return_value = False
        mock_ctrl.is_gamepad_button_pressed.return_value = False
        mock_ctrl.get_gamepad_hat.return_value = (0, 0)
        mock_ctrl.get_gamepad_axis.return_value = 0.0

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        screen._section_index = FighterSelectScreen.SECTION_NAME_DESC
        result = screen.run()
        # Should have exited via Escape, not selection
        assert result is None
        assert screen.quit_requested is False
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_fighter_select.py -v
```
Expected: all tests pass (import, init, navigation, run behavior)

- [ ] **Step 3: Commit**

```bash
git add tests/test_fighter_select.py
git commit -m "test: add unit tests for FighterSelectScreen"
```

---

### Task 9: Run full test suite and verify

**Files:**
- No file changes, verification only

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```
Expected: all existing 52+ tests pass, plus the new fighter_select tests

- [ ] **Step 2: Run import and smoke test**

```bash
python -c "
from game.fighter_select import FighterSelectScreen
from game.fighter import load_all_fighters
fighters = load_all_fighters('game/data/fighters')
screen = FighterSelectScreen(fighters, {}, {}, None, None)
print(f'Loaded {len(screen._fighter_list)} fighters')
for f in screen._fighter_list:
    print(f'  {f.name}: HP={f.base_health} SPD={f.base_speed} PWR={f.base_power}')
"
```
Expected: lists all 4 fighters with their stats

- [ ] **Step 3: Commit any final cleanup**

Only if changes were needed from verification.
