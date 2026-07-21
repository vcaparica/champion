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

    def _move_section(self, direction: int) -> None:
        """Move section selection by +1 or -1. Wraps around."""
        self._section_index = (self._section_index + direction) % self.SECTION_COUNT
        self._play_sfx(self._sfx_move)
        self._announce_section()

    def run(self) -> Optional[FighterData]:
        """Run the fighter selection screen. Returns selected fighter or None."""
        return None
