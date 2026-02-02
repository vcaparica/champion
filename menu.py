"""
menu.py - Accessible Audio Menu System
=======================================
A flexible audio menu system with accessibility features for audiogame
development. Supports keyboard, gamepad buttons, and d-pad navigation
through the unified GameControls system.

Features:
    - Unified input handling via GameControls (keyboard + gamepad)
    - Multiple item types: action, checkbox, radio, slider, submenu
    - Type-ahead search for quick navigation
    - Position announcements and help system
    - Sound effect support for navigation feedback
    - Debounced announcements for rapid navigation
    - Focus memory across menu instances

Gamepad Controls (Xbox-style):
    - D-pad Up/Down or Left Stick: Navigate items
    - A button: Select/activate
    - B button: Back/cancel
    - X button: Repeat current item
    - Y button: Announce title
    - Start: Help
    - Back: Toggle speak mode

Usage:
    from menu import Menu, MenuItem, menu
    from controls import GameControls
    from dj import DJ
    
    controls = GameControls()
    dj = DJ()
    
    items = [
        MenuItem("New Game", id="new_game"),
        MenuItem("Options", id="options"),
        MenuItem("Quit", id="quit"),
    ]
    
    m = Menu("Main Menu", items, controls=controls, dj=dj)
    result = m.run()
    
    # Or use the convenience function:
    result = menu("Main Menu", ["New Game", "Options", "Quit"], controls=controls)

Author: Audiogame Development Project
License: MIT
"""

import pygame
import time
from typing import Any, Callable, List, Optional, Dict, Tuple, Union
from dataclasses import dataclass

from sr import speak, silence
from dj import DJ
from controls import GameControls


class MenuItem:
    """
    Represents a single item within a menu.
    
    Each item can behave as a simple action, checkbox, radio button,
    slider, or submenu. Items can be disabled and include additional
    metadata such as hints for help screens.

    Attributes:
        id: An optional identifier used to identify the item programmatically.
        label: The human-readable text for the item (spoken via TTS).
        audio: Optional path to a .wav file used instead of TTS for the label.
        value: A payload associated with the item. For checkboxes this is a boolean.
        enabled: Whether the item can be selected. Disabled items are skipped.
        hint: Optional hint text or path to .wav for a help description.
        type: One of 'action', 'checkbox', 'radio', 'slider', or 'submenu'.
        group: Optional group identifier used for radio buttons.
        min_value: For sliders, the minimum numeric value.
        max_value: For sliders, the maximum numeric value.
        step: For sliders, the incremental step when adjusting with left/right.
        submenu: If this item opens another menu, assign a list of MenuItem
                 instances here. Selecting the item will push a submenu.
        on_activate: Optional callback invoked when the item is activated. It
                     receives the Menu instance and MenuItem instance.
    """

    def __init__(
        self,
        label: str,
        id: Optional[str] = None,
        audio: Optional[str] = None,
        value: Any = None,
        enabled: bool = True,
        hint: Optional[str] = None,
        type: str = 'action',
        group: Optional[str] = None,
        min_value: float = 0.0,
        max_value: float = 1.0,
        step: float = 0.1,
        submenu: Optional[List['MenuItem']] = None,
        on_activate: Optional[Callable[['Menu', 'MenuItem'], None]] = None
    ):
        self.id = id
        self.label = label
        self.audio = audio
        self.value = value
        self.enabled = enabled
        self.hint = hint
        self.type = type
        self.group = group
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.submenu = submenu
        self.on_activate = on_activate

    def toggle(self):
        """Toggle a checkbox type item."""
        if self.type == 'checkbox':
            self.value = not bool(self.value)

    def adjust(self, delta: float):
        """Adjust a slider type item by delta steps."""
        if self.type == 'slider':
            new_value = float(self.value) + delta * self.step
            new_value = min(self.max_value, max(self.min_value, new_value))
            self.value = new_value

    def set_radio(self, menu: 'Menu'):
        """Set this radio item as selected and clear others in the same group."""
        if self.type != 'radio' or not self.group:
            return
        self.value = True
        for item in menu.items:
            if item is not self and item.group == self.group and item.type == 'radio':
                item.value = False


class Announcer:
    """
    Provides a unified mechanism to announce menu text and play sound effects
    via the supplied DJ instance or TTS.
    
    Implements debouncing and optional suppression of announcements while the
    user scrolls quickly.
    """
    
    def __init__(self, dj: Optional[DJ] = None):
        self.dj = dj or DJ()
        self.last_announce_time: float = 0.0
        self.debounce_delay: float = 0.15  # seconds
        self.speak_on_move: bool = True
        self.position_enabled: bool = False

    def _speak(self, text: str, interrupt: bool = True):
        """Speak text via TTS."""
        speak(text, interrupt)

    def _play_audio(self, path: str):
        """Play a wav file using DJ if possible."""
        self.dj.play_sfx(path)

    def announce(
        self,
        label: str,
        audio: Optional[str] = None,
        position: Optional[str] = None
    ):
        """
        Announce a label, optionally including positional information.
        
        Uses debouncing to avoid chatter when navigating quickly.
        """
        current_time = time.time()
        if not self.speak_on_move:
            # In "speak on focus" mode, we always announce immediately when called.
            self._announce_now(label, audio, position)
            return
        # In speak-on-move mode we use debouncing: skip announcements if called too soon.
        if current_time - self.last_announce_time < self.debounce_delay:
            return
        self._announce_now(label, audio, position)

    def _announce_now(
        self,
        label: str,
        audio: Optional[str] = None,
        position: Optional[str] = None
    ):
        """Announce immediately, optionally adding position and choosing between audio and TTS."""
        self.last_announce_time = time.time()
        announcement = label
        if position and self.position_enabled:
            announcement = f"{announcement}, {position}"
        if audio and audio.endswith('.wav'):
            # Play audio label then optionally speak position separately
            self._play_audio(audio)
            if position and self.position_enabled:
                self._speak(position, False)
        else:
            self._speak(announcement, False)

    def announce_hint(self, hint: Optional[str]):
        """Announce a hint if provided."""
        if not hint:
            return
        if hint.endswith('.wav'):
            self._play_audio(hint)
        else:
            self._speak(hint, False)

    def silence_all(self):
        """Stop all currently playing speech and sound effects."""
        silence()
        try:
            self.dj.stop_all_sfx()
            self.dj.stop_all_bgm()
        except Exception:
            pass


@dataclass
class MenuBindings:
    """
    Defines input bindings for menu navigation.
    
    Each binding is a tuple of (keyboard_keys, gamepad_buttons) where:
        - keyboard_keys: List of pygame key constants
        - gamepad_buttons: List of gamepad button indices
    
    Gamepad button indices follow Xbox-style layout:
        0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=Back, 7=Start
    """
    # Navigation
    prev: Tuple[List[int], List[int]] = None
    next: Tuple[List[int], List[int]] = None
    left: Tuple[List[int], List[int]] = None
    right: Tuple[List[int], List[int]] = None
    
    # Actions
    select: Tuple[List[int], List[int]] = None
    back: Tuple[List[int], List[int]] = None
    
    # Utility
    repeat: Tuple[List[int], List[int]] = None
    hint: Tuple[List[int], List[int]] = None
    title: Tuple[List[int], List[int]] = None
    help: Tuple[List[int], List[int]] = None
    position: Tuple[List[int], List[int]] = None
    toggle_mode: Tuple[List[int], List[int]] = None
    silence: Tuple[List[int], List[int]] = None
    
    # Page navigation
    page_up: Tuple[List[int], List[int]] = None
    page_down: Tuple[List[int], List[int]] = None
    home: Tuple[List[int], List[int]] = None
    end: Tuple[List[int], List[int]] = None
    
    def __post_init__(self):
        """Set default bindings if not provided."""
        # Gamepad button constants (Xbox-style)
        GP_A = 0
        GP_B = 1
        GP_X = 2
        GP_Y = 3
        GP_LB = 4
        GP_RB = 5
        GP_BACK = 6
        GP_START = 7
        
        if self.prev is None:
            self.prev = ([pygame.K_UP], [])
        if self.next is None:
            self.next = ([pygame.K_DOWN], [])
        if self.left is None:
            self.left = ([pygame.K_LEFT], [])
        if self.right is None:
            self.right = ([pygame.K_RIGHT], [])
        if self.select is None:
            self.select = ([pygame.K_RETURN], [GP_A])
        if self.back is None:
            self.back = ([pygame.K_ESCAPE], [GP_B])
        if self.repeat is None:
            self.repeat = ([pygame.K_SPACE], [GP_X])
        if self.hint is None:
            self.hint = ([pygame.K_h], [])
        if self.title is None:
            self.title = ([pygame.K_t], [GP_Y])
        if self.help is None:
            self.help = ([pygame.K_QUESTION, pygame.K_F1], [GP_START])
        if self.position is None:
            self.position = ([pygame.K_p], [])
        if self.toggle_mode is None:
            self.toggle_mode = ([pygame.K_c], [GP_BACK])
        if self.silence is None:
            self.silence = ([pygame.K_LCTRL, pygame.K_RCTRL], [])
        if self.page_up is None:
            self.page_up = ([pygame.K_PAGEUP], [GP_LB])
        if self.page_down is None:
            self.page_down = ([pygame.K_PAGEDOWN], [GP_RB])
        if self.home is None:
            self.home = ([pygame.K_HOME], [])
        if self.end is None:
            self.end = ([pygame.K_END], [])


class Menu:
    """
    Implements a flexible audio menu system with accessibility features.
    
    Menus are composed of MenuItem instances and support navigation via
    keyboard and gamepad (through GameControls), type-ahead search, optional
    paging, and submenus. Audio announcements are managed via the Announcer
    class. Memory of last selected index is shared across menu instances.

    Sound effects can be configured via the sfx_move, sfx_select, and sfx_cancel
    parameters, which accept sound names or indices for the DJ instance.
    
    Gamepad Navigation:
        - D-pad or Left Stick: Navigate up/down (vertical) or left/right (horizontal)
        - A button: Select/activate item
        - B button: Back/cancel
        - X button: Repeat current item
        - Y button: Announce title
        - Start: Help
        - Back: Toggle speak mode
        - LB/RB: Page up/down
    """
    
    # Shared memory of last focused indices per menu title
    _focus_memory: Dict[str, int] = {}
    
    # Axis threshold for d-pad emulation from analog sticks
    AXIS_THRESHOLD = 0.5
    
    # Repeat delay for held inputs (in seconds)
    INPUT_REPEAT_DELAY = 0.3
    INPUT_REPEAT_RATE = 0.08

    def __init__(
        self,
        title: str,
        items: List[MenuItem],
        wrap: bool = True,
        vertical: bool = True,
        dj: Optional[DJ] = None,
        controls: Optional[GameControls] = None,
        bindings: Optional[MenuBindings] = None,
        sfx_move: Optional[str] = None,
        sfx_select: Optional[str] = None,
        sfx_cancel: Optional[str] = None,
        # Legacy parameter for backward compatibility
        keymap: Optional[Dict[str, List[int]]] = None
    ):
        """
        Initialize the menu.
        
        Args:
            title: Menu title (announced when menu opens)
            items: List of MenuItem instances
            wrap: If True, navigation wraps around at ends
            vertical: If True, up/down navigates; if False, left/right navigates
            dj: DJ instance for sound playback
            controls: GameControls instance for unified input
            bindings: Custom MenuBindings for input mapping
            sfx_move: Sound effect name/index for navigation
            sfx_select: Sound effect name/index for selection
            sfx_cancel: Sound effect name/index for cancel/back
            keymap: Legacy keyboard-only keymap (deprecated, use bindings)
        """
        self.title = title
        self.items = items
        self.wrap = wrap
        self.vertical = vertical
        self.dj = dj or DJ()
        self.controls = controls
        self.announcer = Announcer(self.dj)
        
        # Sound effects for menu interactions
        self.sfx_move = sfx_move
        self.sfx_select = sfx_select
        self.sfx_cancel = sfx_cancel
        
        # Input bindings
        self.bindings = bindings or MenuBindings()
        
        # Convert legacy keymap if provided
        if keymap:
            self._convert_legacy_keymap(keymap)
        
        # Current index loaded from memory if available
        self.current_index = Menu._focus_memory.get(self.title, 0)
        if self.current_index >= len(self.items):
            self.current_index = 0
        
        self.running = False
        self.submenu_stack: List[Menu] = []
        self.type_buffer = ''
        self.type_buffer_time = 0.0
        
        # Input repeat tracking for held inputs
        self._last_input_time: Dict[str, float] = {}
        self._input_held: Dict[str, bool] = {}
        
        # Axis state tracking for d-pad emulation
        self._prev_axis_state: Dict[str, int] = {
            'vertical': 0,  # -1 = up, 0 = center, 1 = down
            'horizontal': 0  # -1 = left, 0 = center, 1 = right
        }
    
    def _convert_legacy_keymap(self, keymap: Dict[str, List[int]]):
        """Convert legacy keymap format to MenuBindings."""
        mapping = {
            'prev': 'prev',
            'next': 'next',
            'left': 'left',
            'right': 'right',
            'select': 'select',
            'back': 'back',
            'repeat': 'repeat',
            'hint': 'hint',
            'title': 'title',
            'help': 'help',
            'position': 'position',
            'toggle_mode': 'toggle_mode',
            'silence': 'silence',
            'page_up': 'page_up',
            'page_down': 'page_down',
            'home': 'home',
            'end': 'end'
        }
        
        for old_key, new_key in mapping.items():
            if old_key in keymap:
                # Keep keyboard keys, use default gamepad buttons
                current = getattr(self.bindings, new_key)
                setattr(self.bindings, new_key, (keymap[old_key], current[1]))

    @property
    def items_count(self) -> int:
        return len(self.items)

    def _play_move_sfx(self):
        """Play the movement sound effect if configured."""
        if self.sfx_move is not None:
            try:
                self.dj.play_sfx(self.sfx_move)
            except Exception:
                pass

    def _play_select_sfx(self):
        """Play the selection sound effect if configured."""
        if self.sfx_select is not None:
            try:
                self.dj.play_sfx(self.sfx_select)
            except Exception:
                pass

    def _play_cancel_sfx(self):
        """Play the cancel/back sound effect if configured."""
        if self.sfx_cancel is not None:
            try:
                self.dj.play_sfx(self.sfx_cancel)
            except Exception:
                pass

    def _position_string(self) -> str:
        return f"{self.current_index + 1} of {self.items_count}"

    def _speak_current(self):
        """Announce the current menu item."""
        item = self.items[self.current_index]
        pos = self._position_string()
        
        # Include value information for certain item types
        if item.type == 'checkbox':
            state = 'on' if item.value else 'off'
            label = f"{item.label}: {state}"
        elif item.type == 'slider':
            value_str = f"{item.value:.2f}" if isinstance(item.value, float) else str(item.value)
            label = f"{item.label}: {value_str}"
        elif item.type == 'radio':
            state = 'selected' if item.value else 'not selected'
            label = f"{item.label}, {state}"
        else:
            label = item.label
        
        self.announcer.announce(label, item.audio, pos)

    def _move(self, direction: int):
        """Move selection by a delta of ±1, skipping disabled items."""
        if not self.items:
            return
        orig_index = self.current_index
        for _ in range(self.items_count):
            self.current_index += direction
            if self.current_index < 0:
                if self.wrap:
                    self.current_index = self.items_count - 1
                else:
                    self.current_index = 0
            elif self.current_index >= self.items_count:
                if self.wrap:
                    self.current_index = 0
                else:
                    self.current_index = self.items_count - 1
            item = self.items[self.current_index]
            if item.enabled:
                break
        # Remember focus for this menu
        Menu._focus_memory[self.title] = self.current_index
        if self.current_index != orig_index:
            self._play_move_sfx()
            self._speak_current()

    def _page_move(self, pages: int):
        """Move up or down by a number of items equal to pages*5."""
        step = 5 * pages
        if not self.items:
            return
        orig_index = self.current_index
        idx = self.current_index + step
        if idx < 0:
            idx = 0 if not self.wrap else (self.items_count + idx) % self.items_count
        elif idx >= self.items_count:
            idx = (idx % self.items_count) if self.wrap else (self.items_count - 1)
        self.current_index = idx
        # Skip disabled items
        if not self.items[self.current_index].enabled:
            self._move(1 if step >= 0 else -1)
        else:
            if self.current_index != orig_index:
                self._play_move_sfx()
            self._speak_current()
        Menu._focus_memory[self.title] = self.current_index

    def _home_end(self, to_end: bool):
        """Jump to the first or last enabled item."""
        if not self.items:
            return
        orig_index = self.current_index
        idx_range = range(self.items_count - 1, -1, -1) if to_end else range(self.items_count)
        for idx in idx_range:
            if self.items[idx].enabled:
                self.current_index = idx
                break
        Menu._focus_memory[self.title] = self.current_index
        if self.current_index != orig_index:
            self._play_move_sfx()
        self._speak_current()

    def _repeat(self):
        """Repeat the current item announcement."""
        self._speak_current()

    def _announce_title(self):
        """Announce the menu title."""
        if self.title.endswith('.wav'):
            self.dj.play_sfx(self.title)
        else:
            speak(self.title, False)

    def _announce_help(self):
        """Announce help text summarizing available commands."""
        if self.controls and self.controls.get_gamepad_count() > 0:
            help_text = (
                "Keyboard: Arrow keys to navigate. Enter to select. Escape to go back. "
                "Space repeats the current item. H for hint. T repeats the title. "
                "P announces position. C toggles speak mode. Page Up/Down move by five. "
                "Home/End jump to first/last. Type letters to search. Ctrl silences audio. "
                "Gamepad: D-pad or left stick to navigate. A to select. B to go back. "
                "X repeats item. Y repeats title. Start for help. Back toggles speak mode. "
                "Left and right bumpers for page up/down."
            )
        else:
            help_text = (
                "Use the arrow keys to navigate. Enter to select. Escape to go back. "
                "Space repeats the current item. H for hint. T repeats the title. "
                "P announces position. C toggles between speak-on-move and speak-on-focus. "
                "Page Up/Down move by five. Home/End jump to first/last. "
                "Type letters to search. Ctrl silences audio."
            )
        speak(help_text, False)

    def _toggle_speak_mode(self):
        """Toggle between speak on move and speak on focus modes."""
        self.announcer.speak_on_move = not self.announcer.speak_on_move
        mode = "speak on move" if self.announcer.speak_on_move else "speak on focus"
        speak(f"Mode: {mode}", False)

    def _announce_position(self):
        """Announce the current position in the list."""
        pos = self._position_string()
        speak(pos, False)

    def _process_search(self, char: str):
        """
        Process type-ahead search by accumulating characters and matching labels.
        Resets after a timeout.
        """
        now = time.time()
        if now - self.type_buffer_time > 1.0:
            self.type_buffer = ''
        self.type_buffer += char.lower()
        self.type_buffer_time = now
        # Find the first item whose label starts with the buffer
        orig_index = self.current_index
        for idx, item in enumerate(self.items):
            if not item.enabled:
                continue
            if item.label.lower().startswith(self.type_buffer):
                self.current_index = idx
                Menu._focus_memory[self.title] = self.current_index
                if self.current_index != orig_index:
                    self._play_move_sfx()
                self._speak_current()
                return

    def _handle_activation(self) -> Any:
        """Handle the activation of the current item and return a structured result."""
        item = self.items[self.current_index]
        if not item.enabled:
            speak("This option is disabled.", False)
            return None
        
        # Play selection sound effect
        self._play_select_sfx()
        
        # Custom on_activate callback may override default behaviour
        if item.on_activate:
            try:
                item.on_activate(self, item)
            except Exception:
                pass
        
        if item.type == 'checkbox':
            item.toggle()
            state = 'on' if item.value else 'off'
            speak(f"{item.label}: {state}", False)
            return None
        elif item.type == 'radio':
            item.set_radio(self)
            speak(item.label, False)
            return None
        elif item.type == 'slider':
            value_str = f"{item.value:.2f}" if isinstance(item.value, float) else str(item.value)
            speak(f"{item.label}: {value_str}", False)
            return None
        elif item.type == 'submenu' and item.submenu:
            # Launch submenu with same controls
            submenu = Menu(
                item.label,
                item.submenu,
                self.wrap,
                self.vertical,
                self.dj,
                self.controls,
                self.bindings,
                self.sfx_move,
                self.sfx_select,
                self.sfx_cancel
            )
            result = submenu.run()
            return result
        
        # Default action: return selection result
        return {
            'action': 'selected',
            'id': item.id,
            'value': item.value,
            'label': item.label,
            'path': [self.title, item.label],
        }

    def _adjust_current_item(self, direction: int):
        """Adjust the current item if it is a checkbox, radio, or slider."""
        item = self.items[self.current_index]
        if item.type == 'checkbox':
            item.toggle()
            state = 'on' if item.value else 'off'
            speak(f"{item.label}: {state}", False)
        elif item.type == 'radio':
            # For radio groups, move selection within group
            group_items = [i for i in self.items if i.group == item.group and i.type == 'radio']
            if not group_items:
                return
            current_idx = group_items.index(item)
            new_idx = (current_idx + direction) % len(group_items)
            new_item = group_items[new_idx]
            new_item.set_radio(self)
            self.current_index = self.items.index(new_item)
            Menu._focus_memory[self.title] = self.current_index
            self._play_move_sfx()
            speak(new_item.label, False)
        elif item.type == 'slider':
            item.adjust(direction)
            value_str = f"{item.value:.2f}" if isinstance(item.value, float) else str(item.value)
            speak(f"{item.label}: {value_str}", False)

    def _check_binding_pressed(self, binding: Tuple[List[int], List[int]]) -> bool:
        """Check if any key or button in a binding was just pressed."""
        keys, buttons = binding
        
        # Check keyboard
        for key in keys:
            if self.controls.is_key_pressed(key):
                return True
        
        # Check gamepad buttons
        for button in buttons:
            if self.controls.is_gamepad_button_pressed(button):
                return True
        
        return False
    
    def _check_binding_held(self, binding: Tuple[List[int], List[int]]) -> bool:
        """Check if any key or button in a binding is currently held."""
        keys, buttons = binding
        
        for key in keys:
            if self.controls.is_key_held(key):
                return True
        
        for button in buttons:
            if self.controls.is_gamepad_button_held(button):
                return True
        
        return False
    
    def _get_axis_direction(self, axis_index: int) -> int:
        """
        Get direction from axis value (-1, 0, or 1).
        
        Returns:
            -1 for negative (up/left), 1 for positive (down/right), 0 for center
        """
        value = self.controls.get_gamepad_axis(axis_index)
        if value < -self.AXIS_THRESHOLD:
            return -1
        elif value > self.AXIS_THRESHOLD:
            return 1
        return 0
    
    def _get_hat_direction(self) -> Tuple[int, int]:
        """Get d-pad direction as (horizontal, vertical)."""
        return self.controls.get_gamepad_hat(0)
    
    def _check_input_repeat(self, input_name: str, is_active: bool) -> bool:
        """
        Check if an input should trigger based on repeat timing.
        
        Handles initial press and held-down repeat behavior.
        """
        current_time = time.time()
        
        if not is_active:
            self._input_held[input_name] = False
            self._last_input_time.pop(input_name, None)
            return False
        
        if input_name not in self._last_input_time:
            # First press
            self._last_input_time[input_name] = current_time
            self._input_held[input_name] = False
            return True
        
        elapsed = current_time - self._last_input_time[input_name]
        
        if not self._input_held.get(input_name, False):
            # Waiting for initial repeat delay
            if elapsed >= self.INPUT_REPEAT_DELAY:
                self._input_held[input_name] = True
                self._last_input_time[input_name] = current_time
                return True
        else:
            # In repeat mode
            if elapsed >= self.INPUT_REPEAT_RATE:
                self._last_input_time[input_name] = current_time
                return True
        
        return False

    def _process_gamepad_navigation(self) -> Optional[Tuple[str, int]]:
        """
        Process gamepad analog stick and d-pad for navigation.
        
        Returns:
            Tuple of (direction_type, direction_value) or None
            direction_type: 'vertical' or 'horizontal'
            direction_value: -1 (up/left) or 1 (down/right)
        """
        # Get d-pad state
        hat_x, hat_y = self._get_hat_direction()
        
        # Get analog stick state
        stick_y = self._get_axis_direction(GameControls.AXIS_LEFT_Y)
        stick_x = self._get_axis_direction(GameControls.AXIS_LEFT_X)
        
        # Combine inputs (d-pad takes priority)
        vertical = hat_y if hat_y != 0 else -stick_y  # Invert stick Y (up is negative)
        horizontal = hat_x if hat_x != 0 else stick_x
        
        # Check for vertical movement with repeat handling
        if vertical != 0:
            input_name = f"nav_vertical_{vertical}"
            if self._check_input_repeat(input_name, True):
                # Clear opposite direction
                self._last_input_time.pop(f"nav_vertical_{-vertical}", None)
                return ('vertical', -vertical)  # Return navigation direction
        else:
            self._last_input_time.pop("nav_vertical_1", None)
            self._last_input_time.pop("nav_vertical_-1", None)
        
        # Check for horizontal movement with repeat handling
        if horizontal != 0:
            input_name = f"nav_horizontal_{horizontal}"
            if self._check_input_repeat(input_name, True):
                self._last_input_time.pop(f"nav_horizontal_{-horizontal}", None)
                return ('horizontal', horizontal)
        else:
            self._last_input_time.pop("nav_horizontal_1", None)
            self._last_input_time.pop("nav_horizontal_-1", None)
        
        return None

    def run(self) -> Any:
        """
        Run the menu loop.
        
        Returns a structured object when an action item is selected,
        or a dict with action 'cancel' when the menu is cancelled.
        """
        if not self.items:
            return {'action': 'cancel'}
        
        self.running = True
        clock = pygame.time.Clock()
        
        # Announce title and current option
        self._announce_title()
        self._speak_current()
        
        result: Any = None
        
        # Create local controls if none provided (fallback for standalone usage)
        owns_controls = False
        if self.controls is None:
            self.controls = GameControls(enable_speech=False)
            owns_controls = True
        
        while self.running:
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self._play_cancel_sfx()
                    result = {'action': 'quit'}
                    break
                
                # Let controls process the event
                self.controls.process_event(event)
                
                # Handle text input for type-ahead search (keyboard only)
                if event.type == pygame.KEYDOWN:
                    # Check for Alt+F4
                    if event.key == pygame.K_F4 and (event.mod & pygame.KMOD_ALT):
                        self.running = False
                        self._play_cancel_sfx()
                        result = {'action': 'quit'}
                        break
                    
                    # Type-ahead search
                    char = event.unicode
                    if char and (char.isalnum() or char.isspace()):
                        self._process_search(char)
            
            if not self.running:
                break
            
            # Check bindings for actions (using pressed state for immediate response)
            
            # Silence
            if self._check_binding_pressed(self.bindings.silence):
                self.announcer.silence_all()
            
            # Back/cancel
            elif self._check_binding_pressed(self.bindings.back):
                self.running = False
                self._play_cancel_sfx()
                result = {'action': 'cancel'}
                break
            
            # Repeat current
            elif self._check_binding_pressed(self.bindings.repeat):
                self._repeat()
            
            # Hint
            elif self._check_binding_pressed(self.bindings.hint):
                item = self.items[self.current_index]
                self.announcer.announce_hint(item.hint)
            
            # Title
            elif self._check_binding_pressed(self.bindings.title):
                self._announce_title()
            
            # Help
            elif self._check_binding_pressed(self.bindings.help):
                self._announce_help()
            
            # Position
            elif self._check_binding_pressed(self.bindings.position):
                self._announce_position()
            
            # Toggle mode
            elif self._check_binding_pressed(self.bindings.toggle_mode):
                self._toggle_speak_mode()
            
            # Page up
            elif self._check_binding_pressed(self.bindings.page_up):
                self._page_move(-1)
            
            # Page down
            elif self._check_binding_pressed(self.bindings.page_down):
                self._page_move(1)
            
            # Home
            elif self._check_binding_pressed(self.bindings.home):
                self._home_end(False)
            
            # End
            elif self._check_binding_pressed(self.bindings.end):
                self._home_end(True)
            
            # Select/activate
            elif self._check_binding_pressed(self.bindings.select):
                activation_result = self._handle_activation()
                if activation_result is not None:
                    self.running = False
                    result = activation_result
            
            # Keyboard navigation with repeat support
            elif self._check_binding_pressed(self.bindings.prev) or self._check_binding_held(self.bindings.prev):
                if self._check_input_repeat('kb_prev', self._check_binding_held(self.bindings.prev)):
                    if self.vertical:
                        self._move(-1)
                    else:
                        pass  # In horizontal mode, prev is not used for movement
            
            elif self._check_binding_pressed(self.bindings.next) or self._check_binding_held(self.bindings.next):
                if self._check_input_repeat('kb_next', self._check_binding_held(self.bindings.next)):
                    if self.vertical:
                        self._move(1)
            
            # Left/Right for horizontal navigation or item adjustment
            elif self._check_binding_pressed(self.bindings.left) or self._check_binding_held(self.bindings.left):
                if self._check_input_repeat('kb_left', self._check_binding_held(self.bindings.left)):
                    if not self.vertical:
                        self._move(-1)
                    else:
                        self._adjust_current_item(-1)
            
            elif self._check_binding_pressed(self.bindings.right) or self._check_binding_held(self.bindings.right):
                if self._check_input_repeat('kb_right', self._check_binding_held(self.bindings.right)):
                    if not self.vertical:
                        self._move(1)
                    else:
                        self._adjust_current_item(1)
            
            else:
                # Clear keyboard repeat states when no navigation keys held
                if not self._check_binding_held(self.bindings.prev):
                    self._last_input_time.pop('kb_prev', None)
                if not self._check_binding_held(self.bindings.next):
                    self._last_input_time.pop('kb_next', None)
                if not self._check_binding_held(self.bindings.left):
                    self._last_input_time.pop('kb_left', None)
                if not self._check_binding_held(self.bindings.right):
                    self._last_input_time.pop('kb_right', None)
            
            # Process gamepad analog/d-pad navigation
            nav_result = self._process_gamepad_navigation()
            if nav_result:
                direction_type, direction_value = nav_result
                if direction_type == 'vertical':
                    if self.vertical:
                        self._move(direction_value)
                    # In horizontal mode, vertical doesn't navigate
                elif direction_type == 'horizontal':
                    if not self.vertical:
                        self._move(direction_value)
                    else:
                        # Adjust current item with horizontal input
                        self._adjust_current_item(direction_value)
            
            # Update controls state
            self.controls.update()
            
            clock.tick(60)
        
        # Cleanup local controls if we created them
        if owns_controls:
            self.controls.cleanup()
            self.controls = None
        
        return result


def menu(
    title: str,
    options: List[Any],
    wrap: bool = True,
    vertical: bool = True,
    dj: Optional[DJ] = None,
    controls: Optional[GameControls] = None,
    bindings: Optional[MenuBindings] = None,
    sfx_move: Optional[str] = None,
    sfx_select: Optional[str] = None,
    sfx_cancel: Optional[str] = None,
    # Legacy parameter
    keymap: Optional[Dict[str, List[int]]] = None
) -> Any:
    """
    Convenience function to construct and run a Menu.
    
    The options list may comprise strings or MenuItem instances.
    Strings are implicitly converted to simple action MenuItems.
    
    Args:
        title: Menu title
        options: List of MenuItem instances, strings, or (label, value) tuples
        wrap: If True, navigation wraps at list ends
        vertical: If True, up/down navigates; if False, left/right navigates
        dj: DJ instance for audio
        controls: GameControls instance for input
        bindings: Custom MenuBindings
        sfx_move: Sound effect for navigation
        sfx_select: Sound effect for selection
        sfx_cancel: Sound effect for cancel
        keymap: Legacy keyboard-only keymap (deprecated)
    
    Returns:
        Result dict from Menu.run()
    """
    items: List[MenuItem] = []
    for opt in options:
        if isinstance(opt, MenuItem):
            items.append(opt)
        elif isinstance(opt, tuple) and len(opt) >= 2:
            label, value = opt[0], opt[1]
            items.append(MenuItem(label=label, value=value))
        else:
            items.append(MenuItem(label=str(opt), value=opt))
    
    m = Menu(
        title,
        items,
        wrap,
        vertical,
        dj,
        controls,
        bindings,
        sfx_move,
        sfx_select,
        sfx_cancel,
        keymap
    )
    return m.run()
