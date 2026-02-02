"""
audio_form.py - Audio Form System for Audiogames
=================================================
A Python implementation of BGT's audio_form system, providing a complete
accessible form interface using only screenreader speech and optional
sound feedback.

This module allows creation of dialog-style forms with various control types:
- Buttons (with primary/cancel attributes)
- Input boxes (single-line and multiline, with password masking)
- Checkboxes
- Lists (single and multi-select)
- Progress bars (with optional beeping feedback)
- Status bars

Features:
    - Full keyboard navigation (Tab, Shift+Tab, Alt+hotkey)
    - Text editing with clipboard support (Ctrl+C/X/V/A)
    - Word-by-word and character navigation in input boxes
    - Text selection and highlighting
    - Automatic hotkey extraction from captions (use & prefix)
    - Optional sound effects via DJ module
    - Complete screen reader feedback via sr module
    - Integration with GameControls for unified input handling

Usage:
    from audio_form import AudioForm
    
    form = AudioForm()
    form.create_window("Example Form")
    
    # Create controls (methods return control IDs)
    list_id = form.create_list("&People")
    form.add_list_item(list_id, "Joseph")
    form.add_list_item(list_id, "Samuel")
    
    ok_btn = form.create_button("&OK", primary=True)
    cancel_btn = form.create_button("&Cancel", cancel=True)
    
    # Main loop
    while True:
        form.monitor()
        
        if form.is_pressed(ok_btn):
            # Handle OK
            break
        if form.is_pressed(cancel_btn):
            # Handle Cancel
            break

Requirements:
    - pygame
    - pyperclip (for clipboard support)
    - sr.py module for screen reader output
    - controls.py module for input handling (optional)
    - dj.py module for sound effects (optional)

Author: Audiogame Development Project
License: MIT
"""

from __future__ import annotations

import time
import pygame
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional, List, Union, TYPE_CHECKING

# Try to import pyperclip for clipboard support
try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

if TYPE_CHECKING:
    from dj import DJ
    from controls import GameControls


# =============================================================================
# Constants
# =============================================================================

class ControlType(IntEnum):
    """Types of form controls."""
    BUTTON = 0
    INPUT = 1
    CHECKBOX = 2
    PROGRESS = 3
    STATUS_BAR = 4
    LIST = 5


class FormError(IntEnum):
    """Error codes returned by form operations."""
    NONE = 0
    INVALID_INDEX = 1
    INVALID_CONTROL = 2
    INVALID_VALUE = 3
    INVALID_OPERATION = 4
    NO_WINDOW = 5
    WINDOW_FULL = 6
    TEXT_TOO_LONG = 7
    LIST_EMPTY = 8
    LIST_FULL = 9
    INVALID_LIST_INDEX = 10
    CONTROL_INVISIBLE = 11
    NO_CONTROLS_VISIBLE = 12


class TextFlag(IntEnum):
    """Text entry speech flags for input boxes."""
    NONE = 0
    CHARACTERS = 1
    WORDS = 2
    CHARACTERS_WORDS = 3


class EditMode(IntEnum):
    """Text edit modes for programmatic text modification."""
    REPLACE = 0
    TRIM_TO_LENGTH = 1
    APPEND_TO_END = 2


# Maximum number of controls allowed in a form
MAX_CONTROLS = 50


# =============================================================================
# Helper Classes
# =============================================================================

@dataclass
class ListItem:
    """Represents an item in a list control."""
    text: str = ""
    checked: bool = False


@dataclass
class Control:
    """Internal class representing a form control."""
    type: ControlType = ControlType.BUTTON
    caption: str = ""
    visible: bool = True
    enabled: bool = True
    active: bool = True
    focused: bool = False
    
    # Hotkey properties
    hotkey: int = -1
    hotkey_letter: str = ""
    
    # Button properties
    pressed: bool = False
    primary: bool = False
    cancel: bool = False
    
    # Input box properties
    text: str = ""
    password_mask: str = ""
    max_length: int = 0
    read_only: bool = False
    multiline: bool = False
    overwrite: bool = False
    sel_start: int = -1
    sel_highlight: int = 0
    sel_length: int = 0
    echo_flag: int = TextFlag.CHARACTERS
    
    # Checkbox properties
    checked: bool = False
    
    # Progress bar properties
    progress: int = 0
    speak_interval: int = 5000
    speak_global: bool = False
    beeping_progress: bool = False
    progress_timer: float = 0.0
    progress_timer_running: bool = False
    
    # List properties
    list_items: List[ListItem] = field(default_factory=list)
    list_position: int = -1
    list_multiselect: bool = False
    max_items: int = 0
    
    # Speech configuration
    highlight_selection_text: str = "Selected"
    highlight_unselection_text: str = "Unselected"
    delete_text: str = "Deleted"
    percentage_text: str = "Percent"
    
    def type_to_name(self) -> str:
        """Get the spoken name for this control type."""
        type_names = {
            ControlType.BUTTON: "Button",
            ControlType.INPUT: "Edit" if not self.multiline else "Multiline Edit",
            ControlType.CHECKBOX: "Checkbox",
            ControlType.PROGRESS: "Progress Bar",
            ControlType.STATUS_BAR: "Status Bar",
            ControlType.LIST: "List" if not self.list_multiselect else "Multiselect List",
        }
        return type_names.get(self.type, "Unknown")


# =============================================================================
# Main AudioForm Class
# =============================================================================

class AudioForm:
    """
    Audio-based form system for accessible audiogame interfaces.
    
    Provides a complete dialog/form interface using only screen reader
    speech and optional sound feedback.
    """
    
    def __init__(
        self,
        dj: Optional['DJ'] = None,
        controls: Optional['GameControls'] = None,
        speak_control_attributes_separately: bool = False,
    ) -> None:
        """
        Initialize the audio form system.
        
        Args:
            dj: Optional DJ instance for sound effects.
            controls: Optional GameControls instance for input handling.
            speak_control_attributes_separately: If True, speak control name
                and type as separate utterances.
        """
        self._dj = dj
        self._controls = controls
        self.speak_control_attributes_separately = speak_control_attributes_separately
        
        # Import sr module for speech
        try:
            from sr import speak as sr_speak, silence as sr_silence
            self._speak_func = sr_speak
            self._silence_func = sr_silence
        except ImportError:
            self._speak_func = lambda text, interrupt=True: None
            self._silence_func = lambda: None
        
        # Form state
        self._active = False
        self._controls_list: List[Control] = []
        self._control_focus = -1
        self._form_error = FormError.NONE
        self._quit_requested = False
        self._first_monitor_call = True  # Skip input on first monitor() call
        
        # Keyboard state tracking
        self._keys_down: set = set()
        self._keys_pressed_this_frame: set = set()
        self._text_input_buffer: str = ""
    
    @property
    def quit_requested(self) -> bool:
        """Check if a quit/close event was received."""
        return self._quit_requested
    
    def reset(self) -> None:
        """Reset the form to its initial state."""
        self._form_error = FormError.NONE
        self._active = False
        self._control_focus = -1
        self._controls_list.clear()
    
    # =========================================================================
    # Window and Control Creation
    # =========================================================================
    
    def create_window(
        self,
        window_title: str,
        change_screen_title: bool = True,
        say_dialog: bool = True
    ) -> None:
        """Create and announce the form window."""
        self._form_error = FormError.NONE
        self._active = True
        
        if change_screen_title and window_title:
            pygame.display.set_caption(window_title)
        
        if not window_title:
            return
        
        if self.speak_control_attributes_separately:
            self._speak(window_title, interrupt=True)
            if say_dialog:
                self._speak("Dialog", interrupt=False)
        else:
            if say_dialog:
                self._speak(f"{window_title} Dialog", interrupt=True)
            else:
                self._speak(window_title, interrupt=True)
    
    def create_button(
        self,
        caption: str,
        primary: bool = False,
        cancel: bool = False,
        overwrite: bool = True
    ) -> int:
        """Create a button control. Returns control ID or -1 on error."""
        self._form_error = FormError.NONE
        
        if len(self._controls_list) >= MAX_CONTROLS:
            self._form_error = FormError.WINDOW_FULL
            return -1
        
        hotkey, hotkey_letter = self._extract_hotkey(caption)
        clean_caption = caption.replace("&", "")
        
        control = Control(
            type=ControlType.BUTTON,
            caption=clean_caption,
            hotkey=hotkey,
            hotkey_letter=hotkey_letter,
        )
        
        control_id = len(self._controls_list)
        self._controls_list.append(control)
        self._set_button_attributes(control_id, primary, cancel, overwrite)
        
        return control_id
    
    def create_input_box(
        self,
        caption: str,
        default_text: str = "",
        password_mask: str = "",
        maximum_length: int = 0,
        read_only: bool = False,
        multiline: bool = False
    ) -> int:
        """Create a text input box control. Returns control ID or -1 on error."""
        self._form_error = FormError.NONE
        
        if len(self._controls_list) >= MAX_CONTROLS:
            self._form_error = FormError.WINDOW_FULL
            return -1
        
        hotkey, hotkey_letter = self._extract_hotkey(caption)
        clean_caption = caption.replace("&", "")
        
        if maximum_length > 0 and len(default_text) > maximum_length:
            default_text = default_text[:maximum_length]
            self._form_error = FormError.TEXT_TOO_LONG
        
        control = Control(
            type=ControlType.INPUT,
            caption=clean_caption,
            hotkey=hotkey,
            hotkey_letter=hotkey_letter,
            text=default_text,
            password_mask=password_mask[:1] if password_mask else "",
            max_length=maximum_length,
            read_only=read_only,
            multiline=multiline,
            sel_start=-1,
        )
        
        self._controls_list.append(control)
        return len(self._controls_list) - 1
    
    def create_checkbox(
        self,
        caption: str,
        initial_value: bool = False,
        read_only: bool = False
    ) -> int:
        """Create a checkbox control. Returns control ID or -1 on error."""
        self._form_error = FormError.NONE
        
        if len(self._controls_list) >= MAX_CONTROLS:
            self._form_error = FormError.WINDOW_FULL
            return -1
        
        hotkey, hotkey_letter = self._extract_hotkey(caption)
        clean_caption = caption.replace("&", "")
        
        control = Control(
            type=ControlType.CHECKBOX,
            caption=clean_caption,
            hotkey=hotkey,
            hotkey_letter=hotkey_letter,
            checked=initial_value,
            read_only=read_only,
        )
        
        self._controls_list.append(control)
        return len(self._controls_list) - 1
    
    def create_list(
        self,
        caption: str,
        maximum_items: int = 0,
        multiselect: bool = False
    ) -> int:
        """Create a list control. Returns control ID or -1 on error."""
        self._form_error = FormError.NONE
        
        if len(self._controls_list) >= MAX_CONTROLS:
            self._form_error = FormError.WINDOW_FULL
            return -1
        
        hotkey, hotkey_letter = self._extract_hotkey(caption)
        clean_caption = caption.replace("&", "")
        
        control = Control(
            type=ControlType.LIST,
            caption=clean_caption,
            hotkey=hotkey,
            hotkey_letter=hotkey_letter,
            max_items=maximum_items,
            list_multiselect=multiselect,
            list_position=-1,
        )
        
        self._controls_list.append(control)
        return len(self._controls_list) - 1
    
    def create_progress_bar(
        self,
        caption: str,
        speak_interval: int = 5,
        speak_global: bool = True
    ) -> int:
        """Create a progress bar control. Returns control ID or -1 on error."""
        self._form_error = FormError.NONE
        
        if len(self._controls_list) >= MAX_CONTROLS:
            self._form_error = FormError.WINDOW_FULL
            return -1
        
        hotkey, hotkey_letter = self._extract_hotkey(caption)
        clean_caption = caption.replace("&", "")
        
        can_speak_global = speak_global
        if speak_global:
            for ctrl in self._controls_list:
                if ctrl.type == ControlType.PROGRESS and ctrl.speak_global:
                    can_speak_global = False
                    break
        
        control = Control(
            type=ControlType.PROGRESS,
            caption=clean_caption,
            hotkey=hotkey,
            hotkey_letter=hotkey_letter,
            speak_interval=speak_interval * 1000,
            speak_global=can_speak_global,
            progress=0,
        )
        
        self._controls_list.append(control)
        return len(self._controls_list) - 1
    
    def create_status_bar(self, caption: str, text: str) -> int:
        """Create a status bar control. Returns control ID or -1 on error."""
        self._form_error = FormError.NONE
        
        if len(self._controls_list) >= MAX_CONTROLS:
            self._form_error = FormError.WINDOW_FULL
            return -1
        
        hotkey, hotkey_letter = self._extract_hotkey(caption)
        clean_caption = caption.replace("&", "")
        
        control = Control(
            type=ControlType.STATUS_BAR,
            caption=clean_caption,
            hotkey=hotkey,
            hotkey_letter=hotkey_letter,
            text=text,
        )
        
        self._controls_list.append(control)
        return len(self._controls_list) - 1
    
    # =========================================================================
    # Control Manipulation
    # =========================================================================
    
    def delete_control(self, control_index: int) -> bool:
        """Delete a control from the form."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        self._controls_list[control_index].active = False
        self._control_focus = -1
        return True
    
    def set_state(self, control_index: int, enabled: bool, visible: bool) -> bool:
        """Set the enabled and visible state of a control."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        self._controls_list[control_index].enabled = enabled
        self._controls_list[control_index].visible = visible
        return True
    
    def focus(self, control_index: int) -> bool:
        """Set focus to a specific control."""
        return self._focus(control_index, interrupt=True)
    
    # =========================================================================
    # List Operations
    # =========================================================================
    
    def add_list_item(
        self,
        control_index: int,
        option: str,
        position: int = -1,
        selected: bool = False
    ) -> bool:
        """Add an item to a list control."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        if control.max_items > 0 and len(control.list_items) >= control.max_items:
            self._form_error = FormError.LIST_FULL
            return False
        
        item = ListItem(text=option, checked=selected if control.list_multiselect else False)
        
        if position == -1 or position >= len(control.list_items):
            control.list_items.append(item)
        else:
            control.list_items.insert(max(0, position), item)
        
        return True
    
    def edit_list_item(self, control_index: int, new_option: str, position: int) -> bool:
        """Edit an existing list item's text."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        if position < 0 or position >= len(control.list_items):
            self._form_error = FormError.INVALID_LIST_INDEX
            return False
        
        control.list_items[position].text = new_option
        return True
    
    def delete_list_item(
        self,
        control_index: int,
        list_index: int,
        reset_cursor: bool = True,
        speak_deletion: bool = True
    ) -> bool:
        """Delete an item from a list."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        if list_index < 0 or list_index >= len(control.list_items):
            self._form_error = FormError.INVALID_LIST_INDEX
            return False
        
        if speak_deletion:
            self._speak(f"{control.list_items[list_index].text} deleted.", interrupt=True)
        
        del control.list_items[list_index]
        
        if reset_cursor:
            control.list_position = -1
        else:
            control.list_position = max(0, control.list_position - 1)
            if speak_deletion and control.list_position >= 0 and control.list_items:
                self._speak(control.list_items[control.list_position].text, interrupt=False)
                if control.list_items[control.list_position].checked:
                    self._speak("Checked", interrupt=False)
        
        return True
    
    def clear_list(self, control_index: int) -> bool:
        """Remove all items from a list."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        control.list_items.clear()
        control.list_position = -1
        return True
    
    def get_list_position(self, control_index: int) -> int:
        """Get the current selection position in a list."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return -1
        
        if not self._validate_control_index(control_index):
            return -1
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return -1
        
        return control.list_position
    
    def set_list_position(self, control_index: int, position: int = -1) -> bool:
        """Set the current selection position in a list."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        if position < -1 or position >= len(control.list_items):
            self._form_error = FormError.INVALID_LIST_INDEX
            return False
        
        control.list_position = position
        return True
    
    def get_list_selections(self, control_index: int) -> List[int]:
        """Get indices of all selected items in a list."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return []
        
        if not self._validate_control_index(control_index):
            return []
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return []
        
        if not control.list_multiselect:
            if control.list_position >= 0:
                return [control.list_position]
            return []
        
        selections = [i for i, item in enumerate(control.list_items) if item.checked]
        
        if not selections and control.list_position >= 0:
            return [control.list_position]
        
        return selections
    
    def get_list_count(self, control_index: int) -> int:
        """Get the number of items in a list."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return -1
        
        if not self._validate_control_index(control_index):
            return -1
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return -1
        
        return len(control.list_items)
    
    def get_list_item(self, control_index: int, list_index: int) -> str:
        """Get the text of a specific list item."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return ""
        
        if not self._validate_control_index(control_index):
            return ""
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.LIST:
            self._form_error = FormError.INVALID_CONTROL
            return ""
        
        if list_index < 0 or list_index >= len(control.list_items):
            self._form_error = FormError.INVALID_LIST_INDEX
            return ""
        
        return control.list_items[list_index].text
    
    # =========================================================================
    # Text/Input Operations
    # =========================================================================
    
    def get_text(self, control_index: int) -> str:
        """Get the text content of an input box or status bar."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return ""
        
        if not self._validate_control_index(control_index):
            return ""
        
        control = self._controls_list[control_index]
        
        if control.type not in (ControlType.INPUT, ControlType.STATUS_BAR):
            self._form_error = FormError.INVALID_CONTROL
            return ""
        
        return control.text
    
    def set_text(self, control_index: int, new_text: str) -> bool:
        """Set the text content of an input box or status bar."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type not in (ControlType.INPUT, ControlType.STATUS_BAR):
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        control.text = new_text
        control.sel_start = -1
        return True
    
    # =========================================================================
    # Checkbox Operations
    # =========================================================================
    
    def is_checked(self, control_index: int) -> bool:
        """Check if a checkbox is checked."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.CHECKBOX:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        return control.checked
    
    def set_checkbox_mark(self, control_index: int, checked: bool) -> bool:
        """Set the checked state of a checkbox."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.CHECKBOX:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        control.checked = checked
        return True
    
    # =========================================================================
    # Progress Bar Operations
    # =========================================================================
    
    def get_progress(self, control_index: int) -> int:
        """Get the current progress value (0-100)."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return -1
        
        if not self._validate_control_index(control_index):
            return -1
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.PROGRESS:
            self._form_error = FormError.INVALID_CONTROL
            return -1
        
        return control.progress
    
    def set_progress(self, control_index: int, value: int) -> bool:
        """Set the progress bar value (0-100)."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.PROGRESS:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        if value < 0 or value > 100:
            self._form_error = FormError.INVALID_VALUE
            return False
        
        control.progress = value
        
        if control.speak_interval == 0:
            if control.speak_global or control.focused:
                self._speak_progress(control)
        
        return True
    
    # =========================================================================
    # Button Operations
    # =========================================================================
    
    def is_pressed(self, control_index: int) -> bool:
        """Check if a button was pressed (resets after check)."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if control.type != ControlType.BUTTON:
            self._form_error = FormError.INVALID_CONTROL
            return False
        
        pressed = control.pressed
        control.pressed = False
        return pressed
    
    # =========================================================================
    # State Queries
    # =========================================================================
    
    def get_caption(self, control_index: int) -> str:
        """Get the caption of a control."""
        if not self._active or not self._validate_control_index(control_index):
            return ""
        return self._controls_list[control_index].caption
    
    def get_control_type(self, control_index: int) -> int:
        """Get the type of a control."""
        if not self._active or not self._validate_control_index(control_index):
            return -1
        return self._controls_list[control_index].type
    
    def get_control_count(self) -> int:
        """Get the total number of controls."""
        return len(self._controls_list)
    
    def get_current_focus(self) -> int:
        """Get the index of the currently focused control."""
        if not self._active:
            return -1
        for i, control in enumerate(self._controls_list):
            if control.focused:
                return i
        return -1
    
    def get_default_button(self) -> int:
        """Get the index of the primary (default) button."""
        if not self._active:
            return -1
        for i, control in enumerate(self._controls_list):
            if control.primary:
                return i
        return -1
    
    def get_cancel_button(self) -> int:
        """Get the index of the cancel button."""
        if not self._active:
            return -1
        for i, control in enumerate(self._controls_list):
            if control.cancel:
                return i
        return -1
    
    def is_visible(self, control_index: int) -> bool:
        """Check if a control is visible."""
        if not self._active or not self._validate_control_index(control_index):
            return False
        return self._controls_list[control_index].visible
    
    def is_enabled(self, control_index: int) -> bool:
        """Check if a control is enabled."""
        if not self._active or not self._validate_control_index(control_index):
            return False
        return self._controls_list[control_index].enabled
    
    def get_last_error(self) -> int:
        """Get the last error code."""
        return self._form_error
    
    # =========================================================================
    # Main Monitor Method
    # =========================================================================
    
    def monitor(self) -> bool:
        """
        Process input events and update form state.
        
        Call this method once per frame in your main loop to handle
        keyboard navigation, control interaction, and focus management.
        
        Returns:
            True if the form is still active, False if quit was requested
            (window close button or pygame.QUIT event).
        """
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        defaults = self.get_default_button()
        cancels = self.get_cancel_button()
        focused = self.get_current_focus()
        
        # Process pygame events
        self._text_input_buffer = ""
        self._keys_pressed_this_frame.clear()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_requested = True
                return False
            
            # Always capture TEXTINPUT for input boxes
            if event.type == pygame.TEXTINPUT:
                self._text_input_buffer += event.text
            
            # If GameControls provided, pass events to it for processing
            if self._controls:
                self._controls.process_event(event)
            else:
                # Track our own keyboard state when no GameControls
                if event.type == pygame.KEYDOWN:
                    self._keys_down.add(event.key)
                    self._keys_pressed_this_frame.add(event.key)
                elif event.type == pygame.KEYUP:
                    self._keys_down.discard(event.key)
        
        # Update controls state (transitions PRESSED -> HELD, etc.)
        if self._controls:
            self._controls.update()
        
        # On the first monitor() call, just consume events and update state,
        # but don't process any button/key actions. This prevents input from
        # the previous screen (e.g., the Enter that opened this form) from
        # triggering actions immediately.
        if self._first_monitor_call:
            self._first_monitor_call = False
            return True
        
        # Stop speech on Ctrl+Ctrl
        if self._key_pressed(pygame.K_LCTRL) and self._key_pressed(pygame.K_RCTRL):
            self._silence()
        
        # Handle Tab navigation
        if self._key_pressed(pygame.K_TAB):
            if len(self._controls_list) == 0:
                return True
            if self._key_down(pygame.K_LALT) or self._key_down(pygame.K_LSUPER):
                return True
            
            if self._key_down(pygame.K_LSHIFT) or self._key_down(pygame.K_RSHIFT):
                self._navigate_previous()
            else:
                self._navigate_next()
        
        # Handle Escape for cancel button
        if self._key_pressed(pygame.K_ESCAPE) and cancels >= 0:
            self._controls_list[cancels].pressed = True
        
        # Handle Enter for default button or focused button
        if self._key_pressed(pygame.K_RETURN) or self._key_pressed(pygame.K_KP_ENTER):
            if defaults == -1 and focused >= 0:
                if self._controls_list[focused].type == ControlType.BUTTON:
                    self._controls_list[focused].pressed = True
            elif defaults >= 0:
                if focused == -1:
                    self._controls_list[defaults].pressed = True
                elif focused >= 0:
                    ctrl = self._controls_list[focused]
                    if ctrl.type != ControlType.BUTTON and (ctrl.type != ControlType.INPUT or not ctrl.multiline):
                        self._controls_list[defaults].pressed = True
                    elif ctrl.type == ControlType.BUTTON:
                        ctrl.pressed = True
        
        # Check hotkeys
        self._check_shortcuts()
        
        # Process current control input
        if self._control_focus >= 0:
            self._check_control(self._control_focus)
        
        # Update progress bar timers
        self._update_progress_timers()
        
        return True
    
    # =========================================================================
    # Internal Methods
    # =========================================================================
    
    def _speak(self, text: str, interrupt: bool = True) -> None:
        """Speak text via screen reader."""
        if self._speak_func:
            self._speak_func(text, interrupt)
    
    def _silence(self) -> None:
        """Stop current speech."""
        if self._silence_func:
            self._silence_func()
    
    def _key_down(self, key: int) -> bool:
        """Check if a key is currently held down."""
        if self._controls:
            return self._controls.is_key_held(key)
        return key in self._keys_down
    
    def _key_pressed(self, key: int) -> bool:
        """Check if a key was just pressed this frame."""
        if self._controls:
            return self._controls.is_key_pressed(key)
        return key in self._keys_pressed_this_frame
    
    def _validate_control_index(self, index: int) -> bool:
        """Validate a control index."""
        if index < 0 or index >= len(self._controls_list):
            self._form_error = FormError.INVALID_INDEX
            return False
        if not self._controls_list[index].active:
            self._form_error = FormError.INVALID_CONTROL
            return False
        return True
    
    def _extract_hotkey(self, caption: str) -> tuple:
        """Extract hotkey from caption (letter after &)."""
        for i, char in enumerate(caption):
            if char == "&" and i < len(caption) - 1:
                letter = caption[i + 1]
                key = self._letter_to_key(letter)
                return key, letter
        return -1, ""
    
    def _letter_to_key(self, letter: str) -> int:
        """Convert a letter to pygame key constant."""
        if not letter or not letter.isalnum():
            return -1
        letter = letter.lower()
        if letter.isalpha():
            return getattr(pygame, f"K_{letter}", -1)
        if letter.isdigit():
            return getattr(pygame, f"K_{letter}", -1)
        return -1
    
    def _set_button_attributes(self, control_index: int, primary: bool, cancel: bool, overwrite: bool) -> None:
        """Internal method to set button attributes."""
        control = self._controls_list[control_index]
        
        if primary:
            current_primary = self.get_default_button()
            if current_primary == -1 or overwrite:
                if current_primary >= 0 and current_primary != control_index:
                    self._controls_list[current_primary].primary = False
                control.primary = True
        else:
            control.primary = False
        
        if cancel:
            current_cancel = self.get_cancel_button()
            if current_cancel == -1 or overwrite:
                if current_cancel >= 0 and current_cancel != control_index:
                    self._controls_list[current_cancel].cancel = False
                control.cancel = True
        else:
            control.cancel = False
    
    def _focus(self, control_index: int, interrupt: bool = True) -> bool:
        """Internal method to set focus."""
        self._form_error = FormError.NONE
        
        if not self._active:
            self._form_error = FormError.NO_WINDOW
            return False
        
        if not self._validate_control_index(control_index):
            return False
        
        control = self._controls_list[control_index]
        
        if not control.visible:
            self._form_error = FormError.CONTROL_INVISIBLE
            return False
        
        for i, ctrl in enumerate(self._controls_list):
            if i != control_index:
                ctrl.focused = False
        
        control.focused = True
        self._control_focus = control_index
        self._announce_control(control, interrupt)
        
        return True
    
    def _announce_control(self, control: Control, interrupt: bool = True) -> None:
        """Announce a control when it receives focus."""
        type_name = control.type_to_name()
        
        if self.speak_control_attributes_separately:
            self._speak(control.caption, interrupt)
            self._speak(type_name, interrupt=False)
        else:
            self._speak(f"{control.caption} {type_name}", interrupt)
        
        if control.hotkey_letter:
            self._speak(f"shortcut {control.hotkey_letter}", interrupt=False)
        
        if control.type == ControlType.INPUT:
            if control.password_mask:
                if control.text:
                    self._speak(f"{control.password_mask} times {len(control.text)}", interrupt=False)
            else:
                self._speak(control.text, interrupt=False)
        
        elif control.type == ControlType.STATUS_BAR:
            self._speak(control.text, interrupt=False)
        
        elif control.type == ControlType.CHECKBOX:
            self._speak("Checked" if control.checked else "Unchecked", interrupt=False)
        
        elif control.type == ControlType.PROGRESS:
            self._speak(f"{control.progress} {control.percentage_text}", interrupt=False)
        
        elif control.type == ControlType.LIST:
            if 0 <= control.list_position < len(control.list_items):
                item = control.list_items[control.list_position]
                self._speak(item.text, interrupt=False)
                if item.checked:
                    self._speak("Checked", interrupt=False)
    
    def _navigate_next(self) -> None:
        """Navigate to the next visible control."""
        if len(self._controls_list) == 0:
            return
        
        self._control_focus += 1
        if self._control_focus >= len(self._controls_list):
            self._control_focus = 0
        
        iterations = 0
        while iterations < len(self._controls_list):
            ctrl = self._controls_list[self._control_focus]
            if ctrl.visible and ctrl.active:
                break
            self._control_focus += 1
            if self._control_focus >= len(self._controls_list):
                self._control_focus = 0
            iterations += 1
        
        if iterations >= len(self._controls_list):
            self._form_error = FormError.NO_CONTROLS_VISIBLE
            return
        
        self._focus(self._control_focus, interrupt=True)
    
    def _navigate_previous(self) -> None:
        """Navigate to the previous visible control."""
        if len(self._controls_list) == 0:
            return
        
        self._control_focus -= 1
        if self._control_focus < 0:
            self._control_focus = len(self._controls_list) - 1
        
        iterations = 0
        while iterations < len(self._controls_list):
            ctrl = self._controls_list[self._control_focus]
            if ctrl.visible and ctrl.active:
                break
            self._control_focus -= 1
            if self._control_focus < 0:
                self._control_focus = len(self._controls_list) - 1
            iterations += 1
        
        if iterations >= len(self._controls_list):
            self._form_error = FormError.NO_CONTROLS_VISIBLE
            return
        
        self._focus(self._control_focus, interrupt=True)
    
    def _check_shortcuts(self) -> None:
        """Check for Alt+hotkey combinations."""
        if not self._key_down(pygame.K_LALT):
            return
        
        for i, control in enumerate(self._controls_list):
            if not control.hotkey_letter or not control.visible or not control.active:
                continue
            if control.hotkey >= 0 and self._key_pressed(control.hotkey):
                self._focus(i, interrupt=True)
    
    def _check_control(self, control_index: int) -> None:
        """Process input for the focused control."""
        control = self._controls_list[control_index]
        
        if control.type == ControlType.INPUT and control.focused:
            self._check_input_control(control)
        
        elif control.type == ControlType.BUTTON and control.focused:
            if self._key_pressed(pygame.K_SPACE):
                control.pressed = True
        
        elif control.type == ControlType.LIST:
            self._check_list_control(control)
        
        elif control.type == ControlType.CHECKBOX and control.focused:
            if self._key_pressed(pygame.K_SPACE) and not control.read_only:
                control.checked = not control.checked
                self._speak("Checked" if control.checked else "Unchecked", interrupt=True)
    
    def _check_input_control(self, control: Control) -> None:
        """Handle input for text input controls."""
        if self._text_input_buffer and not control.read_only:
            for char in self._text_input_buffer:
                if control.overwrite:
                    self._edit_char(control, char)
                else:
                    self._add_char(control, char)
        
        ctrl_held = self._key_down(pygame.K_LCTRL) or self._key_down(pygame.K_RCTRL)
        shift_held = self._key_down(pygame.K_LSHIFT) or self._key_down(pygame.K_RSHIFT)
        
        if ctrl_held:
            if self._key_pressed(pygame.K_x) and not control.read_only:
                self._cut_highlighted(control)
            elif self._key_pressed(pygame.K_c):
                self._copy_highlighted(control)
            elif self._key_pressed(pygame.K_v) and not control.read_only:
                self._paste_text(control)
            elif self._key_pressed(pygame.K_a):
                self._highlight_all(control)
        
        if not control.read_only:
            if self._key_pressed(pygame.K_BACKSPACE):
                self._delete_highlighted(control, from_start=0)
            elif self._key_pressed(pygame.K_DELETE):
                self._delete_highlighted(control, from_start=1)
        
        if control.multiline and not control.read_only:
            if self._key_pressed(pygame.K_RETURN) or self._key_pressed(pygame.K_KP_ENTER):
                self._add_char(control, "\r\n")
        
        if self._key_pressed(pygame.K_LEFT):
            if shift_held:
                self._highlight_left(control)
            elif ctrl_held:
                self._move_word_left(control)
            else:
                self._move_left(control)
        
        elif self._key_pressed(pygame.K_RIGHT):
            if shift_held:
                self._highlight_right(control)
            elif ctrl_held:
                self._move_word_right(control)
            else:
                self._move_right(control)
        
        if self._key_pressed(pygame.K_HOME):
            if ctrl_held or not control.multiline:
                if shift_held:
                    self._highlight_to_field_start(control)
                else:
                    self._field_start(control)
        
        if self._key_pressed(pygame.K_END):
            if ctrl_held or not control.multiline:
                if shift_held:
                    self._highlight_to_field_end(control)
                else:
                    self._field_end(control)
    
    def _check_list_control(self, control: Control) -> None:
        """Handle input for list controls."""
        if not control.list_items:
            return
        
        if self._key_pressed(pygame.K_SPACE):
            if control.list_position >= 0 and control.list_multiselect:
                item = control.list_items[control.list_position]
                item.checked = not item.checked
                self._speak("Checked" if item.checked else "Unchecked", interrupt=True)
        
        ctrl_held = self._key_down(pygame.K_LCTRL) or self._key_down(pygame.K_RCTRL)
        if ctrl_held and self._key_pressed(pygame.K_a) and control.list_multiselect:
            for item in control.list_items:
                item.checked = True
            self._speak("All items selected", interrupt=True)
        
        if self._key_pressed(pygame.K_UP):
            if control.list_position > 0:
                control.list_position -= 1
                item = control.list_items[control.list_position]
                self._speak(item.text, interrupt=True)
                if item.checked:
                    self._speak("Checked", interrupt=False)
        
        elif self._key_pressed(pygame.K_DOWN):
            if control.list_position < len(control.list_items) - 1:
                control.list_position += 1
                item = control.list_items[control.list_position]
                self._speak(item.text, interrupt=True)
                if item.checked:
                    self._speak("Checked", interrupt=False)
        
        elif self._key_pressed(pygame.K_HOME):
            if control.list_items:
                control.list_position = 0
                item = control.list_items[0]
                self._speak(item.text, interrupt=True)
                if item.checked:
                    self._speak("Checked", interrupt=False)
        
        elif self._key_pressed(pygame.K_END):
            if control.list_items:
                control.list_position = len(control.list_items) - 1
                item = control.list_items[control.list_position]
                self._speak(item.text, interrupt=True)
                if item.checked:
                    self._speak("Checked", interrupt=False)
    
    # =========================================================================
    # Text Input Helpers
    # =========================================================================
    
    def _get_display_char(self, control: Control, char: str) -> str:
        """Get the display character (handles password mask)."""
        return control.password_mask if control.password_mask else char
    
    def _char_to_speech(self, char: str) -> str:
        """Convert a character to its spoken representation."""
        special_chars = {
            " ": "Space", "\r": "Return", "\n": "New Line", "\r\n": "New Line",
            "\t": "Tab", ".": "Period", ",": "Comma", "!": "Exclamation Mark",
            "?": "Question Mark", "'": "Apostrophe", '"': "Quote", ":": "Colon",
            ";": "Semicolon", "-": "Dash", "_": "Underscore", "=": "Equals",
            "+": "Plus", "@": "At", "#": "Hash", "$": "Dollar", "%": "Percent",
            "^": "Caret", "&": "And", "*": "Star", "(": "Left Parenthesis",
            ")": "Right Parenthesis", "[": "Left Bracket", "]": "Right Bracket",
            "{": "Left Brace", "}": "Right Brace", "<": "Less Than",
            ">": "Greater Than", "/": "Slash", "\\": "Backslash", "|": "Bar",
            "`": "Grave", "~": "Tilde",
        }
        if char in special_chars:
            return special_chars[char]
        if char.isupper():
            return f"Capital {char}"
        return char
    
    def _add_char(self, control: Control, char: str) -> None:
        """Add a character at the cursor position."""
        if control.max_length > 0 and len(control.text) >= control.max_length:
            return
        if control.sel_start == -1:
            control.sel_start = 0
        control.text = control.text[:control.sel_start] + char + control.text[control.sel_start:]
        control.sel_start += len(char)
        control.sel_highlight = control.sel_start
        control.sel_length = 0
        self._speak(self._char_to_speech(self._get_display_char(control, char)), interrupt=True)
    
    def _edit_char(self, control: Control, char: str) -> None:
        """Replace character at cursor position (overwrite mode)."""
        if not control.text or control.sel_start >= len(control.text):
            return
        if control.sel_start == -1:
            control.sel_start = 0
        control.text = control.text[:control.sel_start] + char + control.text[control.sel_start + 1:]
        self._speak(self._char_to_speech(self._get_display_char(control, char)), interrupt=True)
    
    def _move_left(self, control: Control) -> None:
        """Move cursor left by one character."""
        if control.sel_start <= 0:
            return
        if control.sel_start == -1:
            control.sel_start = len(control.text)
        control.sel_start -= 1
        control.sel_length = 0
        if control.sel_start < len(control.text):
            self._speak(self._char_to_speech(self._get_display_char(control, control.text[control.sel_start])), interrupt=True)
    
    def _move_right(self, control: Control) -> None:
        """Move cursor right by one character."""
        if control.sel_start >= len(control.text):
            self._speak("Blank", interrupt=True)
            return
        if control.sel_start == -1:
            control.sel_start = 0
        control.sel_start += 1
        control.sel_length = 0
        if control.sel_start < len(control.text):
            self._speak(self._char_to_speech(self._get_display_char(control, control.text[control.sel_start])), interrupt=True)
        else:
            self._speak("Blank", interrupt=True)
    
    def _move_word_left(self, control: Control) -> None:
        """Move cursor to the beginning of the previous word."""
        if not control.text or control.sel_start <= 0:
            return
        if control.sel_start == -1:
            control.sel_start = len(control.text)
        pos = control.sel_start - 1
        while pos > 0 and control.text[pos] in " \r\n":
            pos -= 1
        while pos > 0 and control.text[pos - 1] not in " \r\n":
            pos -= 1
        control.sel_start = pos
        word = self._read_word_from_position(control, pos)
        self._speak(word, interrupt=True)
    
    def _move_word_right(self, control: Control) -> None:
        """Move cursor to the beginning of the next word."""
        if not control.text or control.sel_start >= len(control.text):
            return
        if control.sel_start == -1:
            control.sel_start = 0
        pos = control.sel_start
        while pos < len(control.text) and control.text[pos] not in " \r\n":
            pos += 1
        while pos < len(control.text) and control.text[pos] in " \r\n":
            pos += 1
        control.sel_start = pos
        if pos >= len(control.text):
            self._speak("Blank", interrupt=True)
        else:
            self._speak(self._read_word_from_position(control, pos), interrupt=True)
    
    def _read_word_from_position(self, control: Control, position: int) -> str:
        """Read a word starting at the given position."""
        word = ""
        for i in range(position, len(control.text)):
            if control.text[i] in " \r\n":
                break
            word += control.text[i]
        return word if word else "Blank"
    
    def _field_start(self, control: Control) -> None:
        """Move cursor to the start of the field."""
        control.sel_start = 0
        control.sel_length = 0
        if control.text:
            self._speak(self._char_to_speech(self._get_display_char(control, control.text[0])), interrupt=True)
    
    def _field_end(self, control: Control) -> None:
        """Move cursor to the end of the field."""
        control.sel_start = len(control.text)
        control.sel_length = 0
        self._speak("Blank", interrupt=True)
    
    def _highlight_left(self, control: Control) -> None:
        """Extend selection to the left."""
        orig_length = control.sel_length
        if control.sel_start <= 0:
            return
        if control.sel_length == 0:
            control.sel_highlight = control.sel_start
        control.sel_start -= 1
        control.sel_length = abs(control.sel_highlight - control.sel_start)
        char = control.text[control.sel_start]
        status = control.highlight_unselection_text if orig_length >= control.sel_length else control.highlight_selection_text
        self._speak(f"{self._char_to_speech(self._get_display_char(control, char))} {status}", interrupt=True)
    
    def _highlight_right(self, control: Control) -> None:
        """Extend selection to the right."""
        orig_length = control.sel_length
        if control.sel_start >= len(control.text):
            return
        if control.sel_length == 0:
            control.sel_highlight = control.sel_start
        control.sel_start += 1
        control.sel_length = abs(control.sel_highlight - control.sel_start)
        if control.sel_start == len(control.text):
            self._speak("Blank", interrupt=True)
        else:
            char = control.text[control.sel_start]
            status = control.highlight_unselection_text if orig_length >= control.sel_length else control.highlight_selection_text
            self._speak(f"{self._char_to_speech(self._get_display_char(control, char))} {status}", interrupt=True)
    
    def _highlight_to_field_start(self, control: Control) -> None:
        """Select from cursor to field start."""
        if control.sel_start <= 0:
            return
        selected_text = control.text[:control.sel_start]
        control.sel_highlight = control.sel_start
        control.sel_start = 0
        control.sel_length = control.sel_highlight
        self._speak(f"{selected_text} {control.highlight_selection_text}", interrupt=True)
    
    def _highlight_to_field_end(self, control: Control) -> None:
        """Select from cursor to field end."""
        if control.sel_start >= len(control.text):
            return
        if control.sel_start == -1:
            control.sel_start = 0
        selected_text = control.text[control.sel_start:]
        control.sel_highlight = control.sel_start
        control.sel_start = len(control.text)
        control.sel_length = control.sel_start - control.sel_highlight
        self._speak(f"{selected_text} {control.highlight_selection_text}", interrupt=True)
    
    def _highlight_all(self, control: Control) -> None:
        """Select all text."""
        control.sel_start = len(control.text)
        control.sel_highlight = 0
        control.sel_length = len(control.text)
        self._speak(f"{control.text} {control.highlight_selection_text}", interrupt=True)
    
    def _copy_highlighted(self, control: Control) -> None:
        """Copy highlighted text to clipboard."""
        if control.sel_length == 0:
            self._speak("Nothing selected", interrupt=True)
            return
        start = min(control.sel_start, control.sel_highlight)
        end = max(control.sel_start, control.sel_highlight)
        copy_text = control.text[start:end]
        if HAS_CLIPBOARD:
            try:
                pyperclip.copy(copy_text)
                self._speak(f"Copied: {copy_text}", interrupt=True)
            except Exception:
                self._speak("Copy failed", interrupt=True)
        else:
            self._speak("Clipboard not available", interrupt=True)
    
    def _cut_highlighted(self, control: Control) -> None:
        """Cut highlighted text to clipboard."""
        if control.read_only:
            self._speak("Cannot cut from a read only edit box.", interrupt=True)
            return
        if control.sel_length == 0:
            self._speak("Nothing selected", interrupt=True)
            return
        start = min(control.sel_start, control.sel_highlight)
        end = max(control.sel_start, control.sel_highlight)
        cut_text = control.text[start:end]
        if HAS_CLIPBOARD:
            try:
                pyperclip.copy(cut_text)
                self._speak(f"Cut: {cut_text}", interrupt=True)
                self._delete_highlighted(control, from_start=0, speak_deleted=False)
            except Exception:
                self._speak("Cut failed", interrupt=True)
        else:
            self._speak("Clipboard not available", interrupt=True)
    
    def _paste_text(self, control: Control) -> None:
        """Paste text from clipboard."""
        if not HAS_CLIPBOARD:
            self._speak("Clipboard not available", interrupt=True)
            return
        try:
            paste = pyperclip.paste()
        except Exception:
            self._speak("Paste failed", interrupt=True)
            return
        if not paste:
            self._speak("There is nothing in the clipboard to paste.", interrupt=True)
            return
        if not control.multiline:
            paste = paste.split("\r\n")[0].split("\n")[0]
        if control.sel_start <= 0:
            control.text = paste + control.text
        elif control.sel_start >= len(control.text):
            control.text += paste
        else:
            control.text = control.text[:control.sel_start] + paste + control.text[control.sel_start:]
        control.sel_start = -1
        self._speak(f"Pasted: {paste}", interrupt=True)
    
    def _delete_highlighted(self, control: Control, from_start: int = 0, speak_deleted: bool = True) -> None:
        """Delete highlighted text or character at cursor."""
        if not control.text or control.read_only:
            return
        if control.sel_length == 0:
            delete_pos = control.sel_start - 1 if from_start == 0 else control.sel_start
            if delete_pos < 0 or delete_pos >= len(control.text):
                return
            deleted_char = control.text[delete_pos]
            if deleted_char == "\r" and delete_pos + 1 < len(control.text) and control.text[delete_pos + 1] == "\n":
                deleted_char = "\r\n"
                control.text = control.text[:delete_pos] + control.text[delete_pos + 2:]
            elif deleted_char == "\n" and delete_pos > 0 and control.text[delete_pos - 1] == "\r":
                deleted_char = "\r\n"
                control.text = control.text[:delete_pos - 1] + control.text[delete_pos + 1:]
                delete_pos -= 1
            else:
                control.text = control.text[:delete_pos] + control.text[delete_pos + 1:]
            if from_start == 0:
                control.sel_start = delete_pos
            if speak_deleted:
                self._speak(f"{self._char_to_speech(deleted_char)} {control.delete_text}", interrupt=True)
        else:
            start = min(control.sel_start, control.sel_highlight)
            end = max(control.sel_start, control.sel_highlight)
            deleted_text = control.text[start:end]
            control.text = control.text[:start] + control.text[end:]
            control.sel_start = start
            control.sel_length = 0
            if speak_deleted:
                self._speak(f"{deleted_text} {control.delete_text}", interrupt=True)
    
    def _update_progress_timers(self) -> None:
        """Update progress bar automatic speech timers."""
        current_time = time.time()
        for control in self._controls_list:
            if control.type != ControlType.PROGRESS or not control.active:
                continue
            if control.speak_interval <= 0:
                continue
            if not control.progress_timer_running:
                control.progress_timer = current_time
                control.progress_timer_running = True
                continue
            elapsed_ms = (current_time - control.progress_timer) * 1000
            if elapsed_ms >= control.speak_interval:
                control.progress_timer = current_time
                if control.speak_global or control.focused:
                    self._speak_progress(control)

    def _speak_progress(self, control: Control) -> None:
        """Speak the current progress value."""
        self._speak(f"{control.progress} {control.percentage_text}", interrupt=True)


# =============================================================================
# Convenience Functions
# =============================================================================

def message_box(
    title: str,
    message: str,
    buttons: List[str] = None,
    dj: Optional['DJ'] = None,
    controls: Optional['GameControls'] = None
) -> int:
    """Display a simple message box dialog. Returns index of pressed button."""
    if buttons is None:
        buttons = ["OK"]
    
    form = AudioForm(dj=dj, controls=controls)
    form.create_window(title)
    form.create_status_bar("Message", message)
    
    button_ids = []
    for i, label in enumerate(buttons):
        btn_id = form.create_button(label, primary=(i == 0), cancel=(i == len(buttons) - 1 and len(buttons) > 1))
        button_ids.append(btn_id)
    
    while True:
        form.monitor()
        for i, btn_id in enumerate(button_ids):
            if form.is_pressed(btn_id):
                return i
        pygame.time.wait(10)


def input_box(
    title: str,
    prompt: str,
    default_text: str = "",
    password: bool = False,
    dj: Optional['DJ'] = None,
    controls: Optional['GameControls'] = None
) -> Optional[str]:
    """Display a simple input dialog. Returns entered text or None if cancelled."""
    form = AudioForm(dj=dj, controls=controls)
    form.create_window(title)
    
    input_id = form.create_input_box(prompt, default_text=default_text, password_mask="*" if password else "")
    ok_btn = form.create_button("&OK", primary=True)
    cancel_btn = form.create_button("&Cancel", cancel=True)
    
    while True:
        form.monitor()
        if form.is_pressed(ok_btn):
            return form.get_text(input_id)
        if form.is_pressed(cancel_btn):
            return None
        pygame.time.wait(10)


def list_box(
    title: str,
    prompt: str,
    items: List[str],
    multiselect: bool = False,
    dj: Optional['DJ'] = None,
    controls: Optional['GameControls'] = None
) -> Optional[Union[int, List[int]]]:
    """Display a list selection dialog. Returns selected index(es) or None."""
    form = AudioForm(dj=dj, controls=controls)
    form.create_window(title)
    
    list_id = form.create_list(prompt, multiselect=multiselect)
    for item in items:
        form.add_list_item(list_id, item)
    if items:
        form.set_list_position(list_id, 0)
    
    ok_btn = form.create_button("&OK", primary=True)
    cancel_btn = form.create_button("&Cancel", cancel=True)
    
    while True:
        form.monitor()
        if form.is_pressed(ok_btn):
            return form.get_list_selections(list_id) if multiselect else form.get_list_position(list_id)
        if form.is_pressed(cancel_btn):
            return None
        pygame.time.wait(10)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "AudioForm", "ControlType", "FormError", "TextFlag", "EditMode",
    "ListItem", "Control", "message_box", "input_box", "list_box",
]

__version__ = "1.0.0"
