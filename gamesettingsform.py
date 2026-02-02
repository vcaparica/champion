"""
gamesettingsform.py - Game Settings Form
=========================================
Provides a Game Settings dialog form for configuring new game parameters.

This module demonstrates using AudioForm to create an accessible settings
dialog with text input, list selection, and button controls.

Usage:
    from gamesettingsform import GameSettingsForm
    
    settings_form = GameSettingsForm(dj=app.dj, controls=app.controls)
    result = settings_form.run()
    
    if result:
        print(f"Table: {result['table_name']}, Format: {result['format']}")

Author: Audiogame Development Project
License: MIT
"""

from __future__ import annotations

import pygame
from typing import Optional, Dict, Any, TYPE_CHECKING

from audio_form import AudioForm
from sr import speak

if TYPE_CHECKING:
    from dj import DJ
    from controls import GameControls


class GameSettingsForm:
    """
    Game Settings form for configuring new game parameters.
    
    Provides a dialog with:
    - Table Name text input
    - Format selection list (Standard, Modern, Limited)
    - OK and Cancel buttons
    
    Example:
        form = GameSettingsForm(dj=my_dj, controls=my_controls)
        result = form.run()
        
        if result is not None:
            # User pressed OK
            table_name = result['table_name']
            format_choice = result['format']
        else:
            # User pressed Cancel
            pass
    """
    
    # Available game formats
    FORMATS = ["Standard", "Modern", "Limited"]
    
    def __init__(
        self,
        dj: Optional['DJ'] = None,
        controls: Optional['GameControls'] = None
    ) -> None:
        """
        Initialize the Game Settings form.
        
        Args:
            dj: Optional DJ instance for sound effects.
            controls: Optional GameControls instance for input handling.
        """
        self._dj = dj
        self._controls = controls
        
        # Form and control IDs
        self._form: Optional[AudioForm] = None
        self._table_name_input: int = -1
        self._format_list: int = -1
        self._ok_button: int = -1
        self._cancel_button: int = -1
    
    def _create_form(self) -> None:
        """Create and initialize the form with all controls."""
        self._form = AudioForm(dj=self._dj, controls=self._controls)
        self._form.create_window("Game Settings", say_dialog=True)
        
        # Create Table Name input field
        self._table_name_input = self._form.create_input_box(
            caption="&Table Name",
            default_text="",
            maximum_length=50
        )
        
        # Create Format selection list
        self._format_list = self._form.create_list(
            caption="&Format",
            maximum_items=0,
            multiselect=False
        )
        
        # Add format options to the list
        for format_name in self.FORMATS:
            self._form.add_list_item(self._format_list, format_name)
        
        # Set default selection to first item
        self._form.set_list_position(self._format_list, 0)
        
        # Create OK button (primary - activates on Enter)
        self._ok_button = self._form.create_button(
            caption="&OK",
            primary=True,
            cancel=False
        )
        
        # Create Cancel button (cancel - activates on Escape)
        self._cancel_button = self._form.create_button(
            caption="&Cancel",
            primary=False,
            cancel=True
        )
    
    def _get_selected_format(self) -> str:
        """Get the currently selected format from the list."""
        position = self._form.get_list_position(self._format_list)
        if position >= 0 and position < len(self.FORMATS):
            return self.FORMATS[position]
        return self.FORMATS[0]  # Default to first format
    
    def _handle_ok(self) -> Dict[str, Any]:
        """Handle OK button press - gather form data and return it."""
        speak("Ok was pressed now!", interrupt=True)
        
        return {
            'table_name': self._form.get_text(self._table_name_input),
            'format': self._get_selected_format(),
            'format_index': self._form.get_list_position(self._format_list)
        }
    
    def _handle_cancel(self) -> None:
        """Handle Cancel button press."""
        # Simply return None to indicate cancellation
        pass
    
    def run(self) -> Optional[Dict[str, Any]]:
        """
        Display and run the Game Settings form.
        
        Returns:
            Dictionary with form data if OK was pressed:
                - 'table_name': str - The entered table name
                - 'format': str - The selected format name
                - 'format_index': int - Index of selected format
            None if Cancel was pressed or form was closed.
        """
        # Create the form
        self._create_form()
        
        # Main form loop
        running = True
        result = None
        
        while running:
            # Monitor the form for input - this handles ALL event processing
            # including pygame events, keyboard state, and control interaction.
            # Note: AudioForm automatically skips input on the first monitor() call
            # to prevent input bleeding from the previous screen.
            if not self._form.monitor():
                # Quit was requested (window closed)
                running = False
                result = None
                continue
            
            # Check for OK button press
            if self._form.is_pressed(self._ok_button):
                result = self._handle_ok()
                running = False
            
            # Check for Cancel button press
            if self._form.is_pressed(self._cancel_button):
                self._handle_cancel()
                result = None
                running = False
            
            # Small delay to prevent CPU spinning
            pygame.time.wait(5)
        
        return result


# =============================================================================
# Standalone test
# =============================================================================

if __name__ == "__main__":
    """Test the Game Settings form standalone."""
    import pygame
    from sr import initialize as sr_initialize
    
    pygame.init()
    pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Game Settings Test")
    
    try:
        sr_initialize()
    except Exception as e:
        print(f"Screen reader init warning: {e}")
    
    # Try to use controls if available
    try:
        from controls import GameControls
        controls = GameControls(enable_speech=False)
    except ImportError:
        controls = None
    
    # Run the form
    form = GameSettingsForm(dj=None, controls=controls)
    result = form.run()
    
    if result:
        print(f"OK pressed!")
        print(f"  Table Name: {result['table_name']}")
        print(f"  Format: {result['format']}")
    else:
        print("Cancelled")
    
    if controls:
        controls.cleanup()
    pygame.quit()
