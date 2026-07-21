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
