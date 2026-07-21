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
