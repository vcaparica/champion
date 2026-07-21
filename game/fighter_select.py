"""
game/fighter_select.py - Fighter Selection Screen for Champion
===============================================================
A 2D-navigable fighter selection screen. Left/right switches between
fighters, up/down browses information sections for the selected fighter.
"""
import pygame
from typing import Optional

from sr import speak
from controls import GameControls
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

            # --- Gamepad d-pad / analog stick navigation ---
            # Process only when no keyboard nav key was pressed this frame
            nav = self._process_gamepad_navigation()
            if nav is not None:
                axis, direction = nav
                if axis == 'fighter':
                    self._move_fighter(direction)
                elif axis == 'section':
                    self._move_section(direction)

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
