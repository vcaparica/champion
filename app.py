import pygame
import time
from typing import Optional

from dj import DJ
from sr import initialize as sr_initialize, speak, silence, shutdown as sr_shutdown
from controls import GameControls
from menu import Menu, MenuItem
from gamesettingsform import GameSettingsForm


class App:
    # Sound effect keys
    SFX_MENU_MOVE = "menu_move"
    SFX_MENU_SELECT = "menu_select"
    SFX_MENU_EXIT = "menu_exit"
    
    # Background music keys
    BGM_MAIN_MENU = "main_menu_bgm"
    
    def __init__(
        self,
        window_title: str = "Audiogame Template",
        window_size: tuple = (800, 600),
        sfx_folder: str = "snd/sfx",
        bgm_folder: str = "snd/bgm",
        bgm_volume: float = 0.7,
        sfx_volume: float = 0.8,
        enable_gamepad_speech: bool = False
    ) -> None:
        """
        Initialize the application.
        
        Args:
            window_title: Title for the game window.
            window_size: Window dimensions (width, height).
            sfx_folder: Path to sound effects folder.
            bgm_folder: Path to background music folder.
            bgm_volume: Master volume for BGM (0.0 - 1.0).
            sfx_volume: Master volume for SFX (0.0 - 1.0).
            enable_gamepad_speech: Enable speech for gamepad events.
        """
        self.window_title = window_title
        self.window_size = window_size
        self.running = True
        
        # Initialize subsystems
        self._init_window()
        self._init_speech()
        
        # Initialize audio system
        self.dj = DJ(
            sfx_folder=sfx_folder,
            bgm_folder=bgm_folder,
            bgm_volume=bgm_volume,
            sfx_volume=sfx_volume
        )
        self._load_sounds()
        
        # Initialize input controls
        self.controls = GameControls(enable_speech=enable_gamepad_speech)
    
    def _init_window(self) -> None:
        """Initialize the pygame display window."""
        self.screen = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption(self.window_title)
        self.screen.fill((0, 0, 0))
        pygame.display.flip()
    
    def _init_speech(self) -> None:
        """Initialize the screen reader speech system."""
        try:
            sr_initialize()
        except Exception as e:
            print(f"Warning: Screen reader initialization issue: {e}")
    
    def _load_sounds(self) -> None:
        """Load all sound effects and background music."""
        self.dj.load_sfx()
        self.dj.load_bgm()
    
    def _play_exit_sfx_and_wait(self) -> None:
        """Play the exit sound effect and wait for it to finish."""
        idx = self.dj.play_sfx(self.SFX_MENU_EXIT)
        if idx >= 0:
            time.sleep(1)
    
    def process_events(self) -> bool:
        """
        Process pygame events.
        
        Returns:
            False if the application should quit, True otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            self.controls.process_event(event)
        return True
    
    def update(self) -> None:
        """
        Update the controls system state.
        
        Call this once per frame after process_events() to transition
        input states (PRESSED -> HELD, etc.) and handle vibration timing.
        """
        self.controls.update()
    
    def _on_new_game(self, menu: Menu, item: MenuItem) -> None:
        """
        Callback for when New Game is selected.
        
        Opens the Game Settings form to configure the new game.
        If the user confirms, the game settings are applied.
        If the user cancels, returns to the main menu.
        """
        # Create and run the Game Settings form
        settings_form = GameSettingsForm(
            dj=self.dj,
            controls=self.controls
        )
        
        result = settings_form.run()
        
        if result is not None:
            # User pressed OK - game settings were confirmed
            # The form already spoke "Ok was pressed now!"
            # Here you would typically start the game with these settings:
            #   result['table_name'] - the table name entered
            #   result['format'] - the selected format (Standard/Modern/Limited)
            #   result['format_index'] - index of selected format
            pass
        else:
            # User pressed Cancel - returning to main menu
            # The menu will re-announce itself when we return
            pass
    
    def _on_options(self, menu: Menu, item: MenuItem) -> None:
        """
        Callback for when Options is selected.
        
        This is a stub method that simply announces the selection.
        Override or replace this method to implement an options menu.
        """
        speak("Menu selection was activated", True)
    
    def main_menu(self) -> None:
        """
        Display and run the main menu loop.
        
        Creates menu items for New Game, Options, and Quit, then
        runs the menu until the user quits via selection, Escape,
        Alt+F4, or closing the window.
        """
        # Start background music
        self.dj.play_bgm(self.BGM_MAIN_MENU, looped=True)
        
        # Define menu items
        menu_items = [
            MenuItem(
                label="New Game",
                id="new_game",
                value="new_game",
                on_activate=self._on_new_game
            ),
            MenuItem(
                label="Options",
                id="options",
                value="options",
                on_activate=self._on_options
            ),
            MenuItem(
                label="Quit",
                id="quit",
                value="quit"
            )
        ]
        
        # Create the main menu
        main_menu = Menu(
            title="Main Menu",
            items=menu_items,
            wrap=True,
            vertical=True,
            dj=self.dj,
            controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE,
            sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT
        )
        
        # Main menu loop
        while self.running:
            result = main_menu.run()
            
            if result is None:
                continue
            
            action = result.get('action')
            
            # Handle quit via menu selection, Escape, Alt+F4, or window close
            if action == 'quit':
                self._handle_quit()
                break
            if action == 'cancel':
                self._handle_quit()
                break
            if action == 'selected':
                item_id = result.get('id')
                if item_id == 'quit':
                    self._handle_quit()
                    break
                
                # For New Game and Options, the on_activate callback
                # already handled the action. We return to the menu.
                # Re-announce the menu title when returning
                speak("Main Menu", False)
    
    def _handle_quit(self) -> None:
        """Handle application quit: stop audio, play exit sound, cleanup."""
        self.running = False
        self.dj.stop_all_bgm()
        self._play_exit_sfx_and_wait()
        self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up all resources before exit."""
        silence()
        self.controls.cleanup()
        self.dj.cleanup()
        try:
            sr_shutdown()
        except Exception:
            pass
    
    def vibrate(
        self,
        low_frequency: float = 0.5,
        high_frequency: float = 0.5,
        duration_ms: int = 100,
        gamepad_id: int = 0
    ) -> bool:
        """
        Vibrate a connected gamepad.
        
        Convenience method that delegates to controls.vibrate().
        
        Args:
            low_frequency: Intensity of heavy motor (0.0 - 1.0)
            high_frequency: Intensity of light motor (0.0 - 1.0)
            duration_ms: Duration in milliseconds
            gamepad_id: Which gamepad to vibrate (default: first)
        
        Returns:
            True if vibration started successfully.
        """
        return self.controls.vibrate(low_frequency, high_frequency, duration_ms, gamepad_id)
    
    def vibrate_pattern(
        self,
        pattern: list,
        gamepad_id: int = 0,
        callback=None
    ) -> None:
        """
        Play a vibration pattern on a gamepad.
        
        Convenience method that delegates to controls.vibrate_pattern().
        
        Args:
            pattern: List of (low_freq, high_freq, duration_ms) tuples
            gamepad_id: Which gamepad to vibrate
            callback: Optional function to call when pattern completes
        """
        self.controls.vibrate_pattern(pattern, gamepad_id, callback)
