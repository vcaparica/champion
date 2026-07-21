# Fighter Selection Screen Design

Date: 2026-07-21
Status: Approved

## Overview

Replace the current simple vertical-menu fighter selection with a rich 2D navigation screen. Left/right switches between fighters, up/down navigates through detailed information about the selected fighter.

## Current State

`app.py:_select_fighter_screen()` (line 364) uses a basic `Menu` with fighter names and truncated 60-char descriptions as labels. It's functional but conveys minimal information and doesn't match the richer presentation used in other parts of the game.

## Goals

- Give players access to full fighter information before choosing
- Provide a more engaging, deliberate selection experience
- Keep the interaction model accessible and screen-reader-first
- Maintain the existing SFX, gamepad, and Alt+F4 conventions

## Design

### Navigation Model (2D)

**Horizontal axis (left/right):** Switches between fighters. Wraps around. Vertical position resets to the top (section 0) on every fighter change. The new fighter's name is announced immediately, then the current section's content.

**Vertical axis (up/down):** Navigates through 5 information sections for the selected fighter. Wraps around.

### Info Sections (0-4, top to bottom)

0. **Name and description** — Fighter name spoken as a heading, then the full lore description from `FighterData.description`.

1. **Stats** — Base stats: health, speed, power. Spoken as "Health 50. Speed 5. Power 8."

2. **Techniques** — Lists all 8 techniques by name with brief descriptions. Left/right within this section navigates through individual technique descriptions in more detail. Techniques are resolved from `App.techniques` dict using the fighter's `technique_ids`.

3. **Equipment** — Items organized by body slot. Each slot's items are listed with their names and descriptions. Resolved from `App.items` using the fighter's `panoply`.

4. **Select this fighter** — "Press Enter to select <fighter name>." Enter confirms immediately and returns the `FighterData`. No confirmation dialog.

### Input Bindings

| Input | Action |
| ----- | ------ |
| Left arrow / D-pad left | Previous fighter (wraps) |
| Right arrow / D-pad right | Next fighter (wraps) |
| Up arrow / D-pad up | Previous info section (wraps) |
| Down arrow / D-pad down | Next info section (wraps) |
| Enter / Gamepad A | Select current fighter (only on section 4) |
| Escape / Gamepad B | Cancel, return None |
| Space / Gamepad X | Repeat current section content |
| H | Speak help text |
| T | Repeat fighter name |
| Alt+F4 | Quit app globally |

### Audio Feedback

- Navigation between fighters or sections plays `sfx_move`
- Selecting a fighter plays `sfx_select`
- Cancelling plays `sfx_cancel`
- All speech uses `sr.speak(text, interrupt=True)` for immediate feedback, matching existing conventions

### Architecture

New file: `game/fighter_select.py`

```python
class FighterSelectScreen:
    def __init__(self, fighters, techniques, items, dj, controls,
                 sfx_move, sfx_select, sfx_cancel):
        ...

    def run(self) -> Optional[FighterData]:
        """Run the selection screen. Returns selected fighter or None."""
        ...
```

The class follows the same pattern as `Menu`: it accepts external `DJ` and `GameControls` instances, runs its own loop, and returns a result. It does not own or clean up the controls.

**Internal state:**
- `fighter_list`: ordered list of `FighterData` from the fighters dict
- `fighter_index`: current horizontal position
- `section_index`: current vertical position (0-4)
- `technique_detail_index`: within section 2, which technique is being examined (0-7)

**Key methods:**
- `run()`: main loop, processes events via `controls`, handles Alt+F4, delegates to navigation methods
- `_announce_fighter()`: speaks fighter name
- `_announce_section()`: speaks current section's content for current fighter
- `_move_fighter(direction)`: change fighter, reset section to 0, announce
- `_move_section(direction)`: change section, announce

### Integration with app.py

Replace the body of `_select_fighter_screen()`:

```python
def _select_fighter_screen(self) -> Optional[object]:
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
    if fighter is None:
        return None
    speak(f"Selected {fighter.name}. {fighter.description}", False)
    return fighter
```

The calling code in `_on_local_match()` and `_on_play_online()` already handles `None` returns correctly (returns to previous screen / disconnects), so no changes needed there.

### Edge Cases

- **One fighter:** Screen still works; left/right do nothing (or wrap to same fighter with boundary SFX).
- **Alt+F4:** Checked every frame with `controls.is_key_pressed(K_F4) + controls.is_modifier_held(KMOD_ALT)`, sets `app.running = False` and returns None. Same pattern as `_wait_for_continue()`.
- **No fighters loaded:** Speak error and return None immediately.
- **Missing technique/item data:** Skip techniques/items whose IDs aren't found in the lookup dicts. Announce count of available techniques/items rather than assuming 8.

### What Does Not Change

- `Menu` and `AudioForm` are untouched
- `FighterData`, `TechniqueData`, `ItemData` are untouched
- `GameControls` and `DJ` are untouched
- `_on_local_match()` and `_on_play_online()` flow is unchanged
- The technique and item selection screens remain as-is
