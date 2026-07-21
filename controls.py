"""
controls.py - Game Controls Input Management
=============================================
A comprehensive input management system for audiogame development,
supporting keyboard, mouse, and gamepad inputs with screen reader
accessibility feedback.

Features:
    - Unified input handling for keyboard, mouse, and gamepad
    - Gamepad support with button, axis, hat, and vibration/rumble
    - Mouse position tracking and button handling
    - Input state queries (pressed, held, released)
    - Automatic device detection and hot-plugging
    - Screen reader friendly with speech output for input events

Usage:
    Basic usage:
        from controls import GameControls
        import pygame
        
        pygame.init()
        pygame.joystick.init()
        
        controls = GameControls()
        
        # In your game loop:
        for event in pygame.event.get():
            controls.process_event(event)
        
        controls.update()  # Call once per frame
        
        if controls.is_key_pressed(pygame.K_SPACE):
            player.jump()
        
        # Vibrate gamepad on hit
        controls.vibrate(low_frequency=0.5, high_frequency=0.8, duration_ms=200)

Requirements:
    - pygame (pip install pygame)
    - sr.py module for screen reader output

Author: Champion Development Project
License: MIT
"""

from __future__ import annotations

import pygame
import time
import threading
from typing import Dict, List, Optional, Set, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum, auto


class InputType(Enum):
    """Types of input devices."""
    KEYBOARD = auto()
    MOUSE = auto()
    GAMEPAD = auto()


class InputState(Enum):
    """State of an input (key, button, etc.)."""
    RELEASED = 0
    PRESSED = 1
    HELD = 2
    JUST_RELEASED = 3


@dataclass
class GamepadState:
    """Stores the current state of a gamepad."""
    id: int
    name: str
    joystick: Optional[pygame.joystick.JoystickType] = None
    buttons: Dict[int, InputState] = field(default_factory=dict)
    axes: Dict[int, float] = field(default_factory=dict)
    hats: Dict[int, Tuple[int, int]] = field(default_factory=dict)
    connected: bool = True
    
    # Axis deadzone threshold
    deadzone: float = 0.15
    
    # Vibration state
    is_vibrating: bool = False
    vibration_end_time: float = 0.0
    
    def get_axis_value(self, axis: int) -> float:
        """Get axis value with deadzone applied."""
        value = self.axes.get(axis, 0.0)
        if abs(value) < self.deadzone:
            return 0.0
        return value
    
    def is_button_pressed(self, button: int) -> bool:
        """Check if button was just pressed this frame."""
        return self.buttons.get(button, InputState.RELEASED) == InputState.PRESSED
    
    def is_button_held(self, button: int) -> bool:
        """Check if button is currently held down."""
        state = self.buttons.get(button, InputState.RELEASED)
        return state in (InputState.PRESSED, InputState.HELD)
    
    def is_button_released(self, button: int) -> bool:
        """Check if button was just released this frame."""
        return self.buttons.get(button, InputState.RELEASED) == InputState.JUST_RELEASED


@dataclass
class MouseState:
    """Stores the current state of the mouse."""
    position: Tuple[int, int] = (0, 0)
    relative_motion: Tuple[int, int] = (0, 0)
    buttons: Dict[int, InputState] = field(default_factory=dict)
    wheel_x: int = 0
    wheel_y: int = 0
    
    # Mouse button constants
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    WHEEL_UP = 4
    WHEEL_DOWN = 5
    
    def is_button_pressed(self, button: int) -> bool:
        """Check if mouse button was just pressed this frame."""
        return self.buttons.get(button, InputState.RELEASED) == InputState.PRESSED
    
    def is_button_held(self, button: int) -> bool:
        """Check if mouse button is currently held down."""
        state = self.buttons.get(button, InputState.RELEASED)
        return state in (InputState.PRESSED, InputState.HELD)
    
    def is_button_released(self, button: int) -> bool:
        """Check if mouse button was just released this frame."""
        return self.buttons.get(button, InputState.RELEASED) == InputState.JUST_RELEASED


class GameControls:
    """
    Manages all input devices for audiogame development.
    
    Provides a unified interface for keyboard, mouse, and gamepad input
    with support for input state tracking, vibration feedback, and
    accessibility features.
    """
    
    # Common gamepad button indices (Xbox-style layout)
    GAMEPAD_A = 0
    GAMEPAD_B = 1
    GAMEPAD_X = 2
    GAMEPAD_Y = 3
    GAMEPAD_LB = 4
    GAMEPAD_RB = 5
    GAMEPAD_BACK = 6
    GAMEPAD_START = 7
    GAMEPAD_GUIDE = 8
    GAMEPAD_L3 = 9
    GAMEPAD_R3 = 10
    
    # Common axis indices
    AXIS_LEFT_X = 0
    AXIS_LEFT_Y = 1
    AXIS_RIGHT_X = 2
    AXIS_RIGHT_Y = 3
    AXIS_LEFT_TRIGGER = 4
    AXIS_RIGHT_TRIGGER = 5
    
    def __init__(self, enable_speech: bool = True) -> None:
        """
        Initialize the controls manager.
        
        Args:
            enable_speech: If True, enable screen reader announcements
                          for input events (useful for testing).
        """
        self.enable_speech = enable_speech
        
        # Keyboard state
        self._keyboard: Dict[int, InputState] = {}
        self._keyboard_pressed_this_frame: Set[int] = set()
        self._keyboard_released_this_frame: Set[int] = set()
        
        # Mouse state
        self.mouse = MouseState()
        self._mouse_buttons_pressed_this_frame: Set[int] = set()
        self._mouse_buttons_released_this_frame: Set[int] = set()
        
        # Gamepad states (supports multiple gamepads)
        self.gamepads: Dict[int, GamepadState] = {}
        self._gamepad_buttons_pressed_this_frame: Dict[int, Set[int]] = {}
        self._gamepad_buttons_released_this_frame: Dict[int, Set[int]] = {}
        
        # Input event callbacks
        self._on_key_press: List[Callable[[int, int], None]] = []
        self._on_key_release: List[Callable[[int, int], None]] = []
        self._on_mouse_press: List[Callable[[int, Tuple[int, int]], None]] = []
        self._on_mouse_release: List[Callable[[int, Tuple[int, int]], None]] = []
        self._on_mouse_move: List[Callable[[Tuple[int, int], Tuple[int, int]], None]] = []
        self._on_mouse_wheel: List[Callable[[int, int], None]] = []
        self._on_gamepad_button_press: List[Callable[[int, int], None]] = []
        self._on_gamepad_button_release: List[Callable[[int, int], None]] = []
        self._on_gamepad_axis: List[Callable[[int, int, float], None]] = []
        self._on_gamepad_hat: List[Callable[[int, int, Tuple[int, int]], None]] = []
        self._on_gamepad_connect: List[Callable[[int, str], None]] = []
        self._on_gamepad_disconnect: List[Callable[[int], None]] = []
        
        # Modifier key tracking
        self._modifiers: int = 0
        
        # Initialize connected gamepads
        self._init_gamepads()
    
    def _init_gamepads(self) -> None:
        """Detect and initialize all connected gamepads."""
        if not pygame.joystick.get_init():
            try:
                pygame.joystick.init()
            except Exception:
                return
        
        count = pygame.joystick.get_count()
        for i in range(count):
            self._add_gamepad(i)
    
    def _add_gamepad(self, device_index: int) -> Optional[GamepadState]:
        """Add a gamepad by device index."""
        try:
            joystick = pygame.joystick.Joystick(device_index)
            joystick.init()
            
            instance_id = joystick.get_instance_id()
            name = joystick.get_name()
            
            gamepad = GamepadState(
                id=instance_id,
                name=name,
                joystick=joystick,
                buttons={i: InputState.RELEASED for i in range(joystick.get_numbuttons())},
                axes={i: 0.0 for i in range(joystick.get_numaxes())},
                hats={i: (0, 0) for i in range(joystick.get_numhats())},
                connected=True
            )
            
            self.gamepads[instance_id] = gamepad
            self._gamepad_buttons_pressed_this_frame[instance_id] = set()
            self._gamepad_buttons_released_this_frame[instance_id] = set()
            
            if self.enable_speech:
                self._speak(f"Gamepad connected: {name}")
            
            for callback in self._on_gamepad_connect:
                try:
                    callback(instance_id, name)
                except Exception:
                    pass
            
            return gamepad
            
        except Exception as e:
            if self.enable_speech:
                self._speak(f"Failed to initialize gamepad: {e}")
            return None
    
    def _remove_gamepad(self, instance_id: int) -> None:
        """Remove a disconnected gamepad."""
        if instance_id in self.gamepads:
            name = self.gamepads[instance_id].name
            del self.gamepads[instance_id]
            
            if instance_id in self._gamepad_buttons_pressed_this_frame:
                del self._gamepad_buttons_pressed_this_frame[instance_id]
            if instance_id in self._gamepad_buttons_released_this_frame:
                del self._gamepad_buttons_released_this_frame[instance_id]
            
            if self.enable_speech:
                self._speak(f"Gamepad disconnected: {name}")
            
            for callback in self._on_gamepad_disconnect:
                try:
                    callback(instance_id)
                except Exception:
                    pass
    
    def _speak(self, text: str, interrupt: bool = True) -> None:
        """Speak text via screen reader if enabled."""
        if not self.enable_speech:
            return
        try:
            from sr import speak
            speak(text, interrupt)
        except ImportError:
            pass
    
    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Process a pygame event and update input states.
        
        Args:
            event: A pygame event to process.
        
        Returns:
            True if the event was handled by the controls system.
        """
        # Keyboard events
        if event.type == pygame.KEYDOWN:
            return self._handle_key_down(event)
        elif event.type == pygame.KEYUP:
            return self._handle_key_up(event)
        
        # Mouse events
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouse_button_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            return self._handle_mouse_button_up(event)
        elif event.type == pygame.MOUSEMOTION:
            return self._handle_mouse_motion(event)
        elif event.type == pygame.MOUSEWHEEL:
            return self._handle_mouse_wheel(event)
        
        # Gamepad events
        elif event.type == pygame.JOYBUTTONDOWN:
            return self._handle_gamepad_button_down(event)
        elif event.type == pygame.JOYBUTTONUP:
            return self._handle_gamepad_button_up(event)
        elif event.type == pygame.JOYAXISMOTION:
            return self._handle_gamepad_axis(event)
        elif event.type == pygame.JOYHATMOTION:
            return self._handle_gamepad_hat(event)
        elif event.type == pygame.JOYDEVICEADDED:
            return self._handle_gamepad_added(event)
        elif event.type == pygame.JOYDEVICEREMOVED:
            return self._handle_gamepad_removed(event)
        
        return False
    
    def _handle_key_down(self, event: pygame.event.Event) -> bool:
        """Handle keyboard key press."""
        key = event.key
        self._modifiers = event.mod
        
        if self._keyboard.get(key) in (None, InputState.RELEASED, InputState.JUST_RELEASED):
            self._keyboard[key] = InputState.PRESSED
            self._keyboard_pressed_this_frame.add(key)
            
            for callback in self._on_key_press:
                try:
                    callback(key, event.mod)
                except Exception:
                    pass
        
        return True
    
    def _handle_key_up(self, event: pygame.event.Event) -> bool:
        """Handle keyboard key release."""
        key = event.key
        self._modifiers = event.mod
        
        self._keyboard[key] = InputState.JUST_RELEASED
        self._keyboard_released_this_frame.add(key)
        
        for callback in self._on_key_release:
            try:
                callback(key, event.mod)
            except Exception:
                pass
        
        return True
    
    def _handle_mouse_button_down(self, event: pygame.event.Event) -> bool:
        """Handle mouse button press."""
        button = event.button
        
        if self.mouse.buttons.get(button) in (None, InputState.RELEASED, InputState.JUST_RELEASED):
            self.mouse.buttons[button] = InputState.PRESSED
            self._mouse_buttons_pressed_this_frame.add(button)
            
            for callback in self._on_mouse_press:
                try:
                    callback(button, event.pos)
                except Exception:
                    pass
        
        return True
    
    def _handle_mouse_button_up(self, event: pygame.event.Event) -> bool:
        """Handle mouse button release."""
        button = event.button
        
        self.mouse.buttons[button] = InputState.JUST_RELEASED
        self._mouse_buttons_released_this_frame.add(button)
        
        for callback in self._on_mouse_release:
            try:
                callback(button, event.pos)
            except Exception:
                pass
        
        return True
    
    def _handle_mouse_motion(self, event: pygame.event.Event) -> bool:
        """Handle mouse movement."""
        old_pos = self.mouse.position
        self.mouse.position = event.pos
        self.mouse.relative_motion = event.rel
        
        for callback in self._on_mouse_move:
            try:
                callback(event.pos, event.rel)
            except Exception:
                pass
        
        return True
    
    def _handle_mouse_wheel(self, event: pygame.event.Event) -> bool:
        """Handle mouse wheel scroll."""
        self.mouse.wheel_x = event.x
        self.mouse.wheel_y = event.y
        
        for callback in self._on_mouse_wheel:
            try:
                callback(event.x, event.y)
            except Exception:
                pass
        
        return True
    
    def _handle_gamepad_button_down(self, event: pygame.event.Event) -> bool:
        """Handle gamepad button press."""
        instance_id = event.instance_id
        button = event.button
        
        if instance_id not in self.gamepads:
            return False
        
        gamepad = self.gamepads[instance_id]
        
        if gamepad.buttons.get(button) in (None, InputState.RELEASED, InputState.JUST_RELEASED):
            gamepad.buttons[button] = InputState.PRESSED
            self._gamepad_buttons_pressed_this_frame[instance_id].add(button)
            
            for callback in self._on_gamepad_button_press:
                try:
                    callback(instance_id, button)
                except Exception:
                    pass
        
        return True
    
    def _handle_gamepad_button_up(self, event: pygame.event.Event) -> bool:
        """Handle gamepad button release."""
        instance_id = event.instance_id
        button = event.button
        
        if instance_id not in self.gamepads:
            return False
        
        gamepad = self.gamepads[instance_id]
        gamepad.buttons[button] = InputState.JUST_RELEASED
        self._gamepad_buttons_released_this_frame[instance_id].add(button)
        
        for callback in self._on_gamepad_button_release:
            try:
                callback(instance_id, button)
            except Exception:
                pass
        
        return True
    
    def _handle_gamepad_axis(self, event: pygame.event.Event) -> bool:
        """Handle gamepad axis motion."""
        instance_id = event.instance_id
        axis = event.axis
        value = event.value
        
        if instance_id not in self.gamepads:
            return False
        
        gamepad = self.gamepads[instance_id]
        gamepad.axes[axis] = value
        
        for callback in self._on_gamepad_axis:
            try:
                callback(instance_id, axis, value)
            except Exception:
                pass
        
        return True
    
    def _handle_gamepad_hat(self, event: pygame.event.Event) -> bool:
        """Handle gamepad hat/d-pad motion."""
        instance_id = event.instance_id
        hat = event.hat
        value = event.value
        
        if instance_id not in self.gamepads:
            return False
        
        gamepad = self.gamepads[instance_id]
        gamepad.hats[hat] = value
        
        for callback in self._on_gamepad_hat:
            try:
                callback(instance_id, hat, value)
            except Exception:
                pass
        
        return True
    
    def _handle_gamepad_added(self, event: pygame.event.Event) -> bool:
        """Handle gamepad connection."""
        device_index = event.device_index
        self._add_gamepad(device_index)
        return True
    
    def _handle_gamepad_removed(self, event: pygame.event.Event) -> bool:
        """Handle gamepad disconnection."""
        instance_id = event.instance_id
        self._remove_gamepad(instance_id)
        return True
    
    def update(self) -> None:
        """
        Update input states at the end of each frame.
        
        Call this once per frame after processing all events to
        transition input states (PRESSED -> HELD, JUST_RELEASED -> RELEASED)
        and handle vibration timing.
        """
        # Update keyboard states
        for key in list(self._keyboard.keys()):
            state = self._keyboard[key]
            if state == InputState.PRESSED:
                self._keyboard[key] = InputState.HELD
            elif state == InputState.JUST_RELEASED:
                self._keyboard[key] = InputState.RELEASED
        
        self._keyboard_pressed_this_frame.clear()
        self._keyboard_released_this_frame.clear()
        
        # Update mouse button states
        for button in list(self.mouse.buttons.keys()):
            state = self.mouse.buttons[button]
            if state == InputState.PRESSED:
                self.mouse.buttons[button] = InputState.HELD
            elif state == InputState.JUST_RELEASED:
                self.mouse.buttons[button] = InputState.RELEASED
        
        self._mouse_buttons_pressed_this_frame.clear()
        self._mouse_buttons_released_this_frame.clear()
        self.mouse.wheel_x = 0
        self.mouse.wheel_y = 0
        self.mouse.relative_motion = (0, 0)
        
        # Update gamepad states and check vibration timeouts
        current_time = time.time()
        for instance_id, gamepad in self.gamepads.items():
            # Update button states
            for button in list(gamepad.buttons.keys()):
                state = gamepad.buttons[button]
                if state == InputState.PRESSED:
                    gamepad.buttons[button] = InputState.HELD
                elif state == InputState.JUST_RELEASED:
                    gamepad.buttons[button] = InputState.RELEASED
            
            if instance_id in self._gamepad_buttons_pressed_this_frame:
                self._gamepad_buttons_pressed_this_frame[instance_id].clear()
            if instance_id in self._gamepad_buttons_released_this_frame:
                self._gamepad_buttons_released_this_frame[instance_id].clear()
            
            # Check vibration timeout
            if gamepad.is_vibrating and current_time >= gamepad.vibration_end_time:
                self._stop_vibration_internal(gamepad)
    
    # -------------------------------------------------------------------------
    # Keyboard State Queries
    # -------------------------------------------------------------------------
    
    def is_key_pressed(self, key: int) -> bool:
        """Check if a key was just pressed this frame."""
        return self._keyboard.get(key) == InputState.PRESSED
    
    def is_key_held(self, key: int) -> bool:
        """Check if a key is currently held down."""
        state = self._keyboard.get(key, InputState.RELEASED)
        return state in (InputState.PRESSED, InputState.HELD)
    
    def is_key_released(self, key: int) -> bool:
        """Check if a key was just released this frame."""
        return self._keyboard.get(key) == InputState.JUST_RELEASED
    
    def get_modifiers(self) -> int:
        """Get current modifier key state (KMOD_* flags)."""
        return self._modifiers
    
    def is_modifier_held(self, mod: int) -> bool:
        """Check if a modifier key is held (e.g., pygame.KMOD_CTRL)."""
        return bool(self._modifiers & mod)
    
    # -------------------------------------------------------------------------
    # Mouse State Queries
    # -------------------------------------------------------------------------
    
    def is_mouse_pressed(self, button: int) -> bool:
        """Check if a mouse button was just pressed this frame."""
        return self.mouse.is_button_pressed(button)
    
    def is_mouse_held(self, button: int) -> bool:
        """Check if a mouse button is currently held down."""
        return self.mouse.is_button_held(button)
    
    def is_mouse_released(self, button: int) -> bool:
        """Check if a mouse button was just released this frame."""
        return self.mouse.is_button_released(button)
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return self.mouse.position
    
    def get_mouse_motion(self) -> Tuple[int, int]:
        """Get mouse motion delta this frame."""
        return self.mouse.relative_motion
    
    def get_mouse_wheel(self) -> Tuple[int, int]:
        """Get mouse wheel scroll this frame (x, y)."""
        return (self.mouse.wheel_x, self.mouse.wheel_y)
    
    # -------------------------------------------------------------------------
    # Gamepad State Queries
    # -------------------------------------------------------------------------
    
    def get_gamepad(self, instance_id: int = 0) -> Optional[GamepadState]:
        """
        Get a gamepad by instance ID.
        
        If instance_id is 0 and no gamepad with ID 0 exists,
        returns the first available gamepad.
        """
        if instance_id in self.gamepads:
            return self.gamepads[instance_id]
        if instance_id == 0 and self.gamepads:
            return next(iter(self.gamepads.values()))
        return None
    
    def get_all_gamepads(self) -> List[GamepadState]:
        """Get all connected gamepads."""
        return list(self.gamepads.values())
    
    def get_gamepad_count(self) -> int:
        """Get number of connected gamepads."""
        return len(self.gamepads)
    
    def is_gamepad_button_pressed(self, button: int, gamepad_id: int = 0) -> bool:
        """Check if a gamepad button was just pressed this frame."""
        gamepad = self.get_gamepad(gamepad_id)
        return gamepad.is_button_pressed(button) if gamepad else False
    
    def is_gamepad_button_held(self, button: int, gamepad_id: int = 0) -> bool:
        """Check if a gamepad button is currently held down."""
        gamepad = self.get_gamepad(gamepad_id)
        return gamepad.is_button_held(button) if gamepad else False
    
    def is_gamepad_button_released(self, button: int, gamepad_id: int = 0) -> bool:
        """Check if a gamepad button was just released this frame."""
        gamepad = self.get_gamepad(gamepad_id)
        return gamepad.is_button_released(button) if gamepad else False
    
    def get_gamepad_axis(self, axis: int, gamepad_id: int = 0) -> float:
        """Get gamepad axis value (-1.0 to 1.0) with deadzone applied."""
        gamepad = self.get_gamepad(gamepad_id)
        return gamepad.get_axis_value(axis) if gamepad else 0.0
    
    def get_gamepad_hat(self, hat: int = 0, gamepad_id: int = 0) -> Tuple[int, int]:
        """Get gamepad hat/d-pad value as (x, y)."""
        gamepad = self.get_gamepad(gamepad_id)
        return gamepad.hats.get(hat, (0, 0)) if gamepad else (0, 0)
    
    # -------------------------------------------------------------------------
    # Gamepad Vibration / Rumble
    # -------------------------------------------------------------------------
    
    def vibrate(
        self,
        low_frequency: float = 0.5,
        high_frequency: float = 0.5,
        duration_ms: int = 100,
        gamepad_id: int = 0
    ) -> bool:
        """
        Vibrate/rumble a gamepad.
        
        Args:
            low_frequency: Intensity of low-frequency (heavy) motor (0.0 to 1.0).
            high_frequency: Intensity of high-frequency (light) motor (0.0 to 1.0).
            duration_ms: Duration of vibration in milliseconds.
            gamepad_id: Which gamepad to vibrate (0 = first/default).
        
        Returns:
            True if vibration was started successfully, False otherwise.
        
        Note:
            Not all gamepads support vibration. This uses pygame's rumble API
            which requires pygame 2.0.1+ and a compatible gamepad.
        
        Example:
            # Strong rumble for damage feedback
            controls.vibrate(1.0, 1.0, 300)
            
            # Gentle pulse for UI feedback
            controls.vibrate(0.2, 0.4, 50)
            
            # Heavy motor only (deep rumble)
            controls.vibrate(0.8, 0.0, 200)
        """
        gamepad = self.get_gamepad(gamepad_id)
        if not gamepad or not gamepad.joystick:
            return False
        
        # Clamp values
        low_frequency = max(0.0, min(1.0, low_frequency))
        high_frequency = max(0.0, min(1.0, high_frequency))
        duration_ms = max(0, duration_ms)
        
        try:
            # pygame.joystick.Joystick.rumble(low_frequency, high_frequency, duration)
            # Returns True if rumble was successfully started
            result = gamepad.joystick.rumble(low_frequency, high_frequency, duration_ms)
            
            if result:
                gamepad.is_vibrating = True
                gamepad.vibration_end_time = time.time() + (duration_ms / 1000.0)
            
            return result
            
        except (AttributeError, pygame.error):
            # rumble() not available or failed
            return False
    
    def stop_vibration(self, gamepad_id: int = 0) -> bool:
        """
        Stop vibration on a gamepad immediately.
        
        Args:
            gamepad_id: Which gamepad to stop vibrating.
        
        Returns:
            True if vibration was stopped, False if gamepad not found.
        """
        gamepad = self.get_gamepad(gamepad_id)
        if not gamepad:
            return False
        
        return self._stop_vibration_internal(gamepad)
    
    def _stop_vibration_internal(self, gamepad: GamepadState) -> bool:
        """Internal method to stop vibration."""
        if not gamepad.joystick:
            return False
        
        try:
            gamepad.joystick.stop_rumble()
            gamepad.is_vibrating = False
            gamepad.vibration_end_time = 0.0
            return True
        except (AttributeError, pygame.error):
            gamepad.is_vibrating = False
            return False
    
    def stop_all_vibration(self) -> None:
        """Stop vibration on all connected gamepads."""
        for gamepad in self.gamepads.values():
            self._stop_vibration_internal(gamepad)
    
    def is_vibrating(self, gamepad_id: int = 0) -> bool:
        """Check if a gamepad is currently vibrating."""
        gamepad = self.get_gamepad(gamepad_id)
        return gamepad.is_vibrating if gamepad else False
    
    def vibrate_pattern(
        self,
        pattern: List[Tuple[float, float, int]],
        gamepad_id: int = 0,
        callback: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Play a vibration pattern asynchronously.
        
        Args:
            pattern: List of (low_freq, high_freq, duration_ms) tuples.
            gamepad_id: Which gamepad to vibrate.
            callback: Optional function to call when pattern completes.
        
        Example:
            # Heartbeat pattern
            controls.vibrate_pattern([
                (0.8, 0.3, 100),  # thump
                (0.0, 0.0, 100),  # pause
                (0.6, 0.2, 80),   # thump
                (0.0, 0.0, 400),  # longer pause
            ])
            
            # Damage taken pattern
            controls.vibrate_pattern([
                (1.0, 1.0, 150),
                (0.3, 0.5, 100),
                (0.1, 0.2, 50),
            ])
        """
        def _play_pattern():
            gamepad = self.get_gamepad(gamepad_id)
            if not gamepad:
                return
            
            for low, high, duration in pattern:
                if low == 0.0 and high == 0.0:
                    # This is a pause
                    self.stop_vibration(gamepad_id)
                    time.sleep(duration / 1000.0)
                else:
                    self.vibrate(low, high, duration, gamepad_id)
                    time.sleep(duration / 1000.0)
            
            self.stop_vibration(gamepad_id)
            
            if callback:
                try:
                    callback()
                except Exception:
                    pass
        
        # Run pattern in background thread
        thread = threading.Thread(target=_play_pattern, daemon=True)
        thread.start()
    
    # -------------------------------------------------------------------------
    # Callback Registration
    # -------------------------------------------------------------------------
    
    def on_key_press(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback for key press events. Args: (key, modifiers)"""
        self._on_key_press.append(callback)
    
    def on_key_release(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback for key release events. Args: (key, modifiers)"""
        self._on_key_release.append(callback)
    
    def on_mouse_press(self, callback: Callable[[int, Tuple[int, int]], None]) -> None:
        """Register a callback for mouse press events. Args: (button, position)"""
        self._on_mouse_press.append(callback)
    
    def on_mouse_release(self, callback: Callable[[int, Tuple[int, int]], None]) -> None:
        """Register a callback for mouse release events. Args: (button, position)"""
        self._on_mouse_release.append(callback)
    
    def on_mouse_move(self, callback: Callable[[Tuple[int, int], Tuple[int, int]], None]) -> None:
        """Register a callback for mouse move events. Args: (position, relative)"""
        self._on_mouse_move.append(callback)
    
    def on_mouse_wheel(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback for mouse wheel events. Args: (x, y)"""
        self._on_mouse_wheel.append(callback)
    
    def on_gamepad_button_press(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback for gamepad button press. Args: (gamepad_id, button)"""
        self._on_gamepad_button_press.append(callback)
    
    def on_gamepad_button_release(self, callback: Callable[[int, int], None]) -> None:
        """Register a callback for gamepad button release. Args: (gamepad_id, button)"""
        self._on_gamepad_button_release.append(callback)
    
    def on_gamepad_axis(self, callback: Callable[[int, int, float], None]) -> None:
        """Register a callback for gamepad axis motion. Args: (gamepad_id, axis, value)"""
        self._on_gamepad_axis.append(callback)
    
    def on_gamepad_hat(self, callback: Callable[[int, int, Tuple[int, int]], None]) -> None:
        """Register a callback for gamepad hat motion. Args: (gamepad_id, hat, value)"""
        self._on_gamepad_hat.append(callback)
    
    def on_gamepad_connect(self, callback: Callable[[int, str], None]) -> None:
        """Register a callback for gamepad connection. Args: (gamepad_id, name)"""
        self._on_gamepad_connect.append(callback)
    
    def on_gamepad_disconnect(self, callback: Callable[[int], None]) -> None:
        """Register a callback for gamepad disconnection. Args: (gamepad_id,)"""
        self._on_gamepad_disconnect.append(callback)
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def get_key_name(self, key: int) -> str:
        """Get the human-readable name of a key."""
        return pygame.key.name(key)
    
    def get_gamepad_button_name(self, button: int) -> str:
        """Get a descriptive name for a gamepad button."""
        button_names = {
            0: "A",
            1: "B",
            2: "X",
            3: "Y",
            4: "Left Bumper",
            5: "Right Bumper",
            6: "Back",
            7: "Start",
            8: "Guide",
            9: "Left Stick",
            10: "Right Stick",
        }
        return button_names.get(button, f"Button {button}")
    
    def get_gamepad_axis_name(self, axis: int) -> str:
        """Get a descriptive name for a gamepad axis."""
        axis_names = {
            0: "Left Stick X",
            1: "Left Stick Y",
            2: "Right Stick X",
            3: "Right Stick Y",
            4: "Left Trigger",
            5: "Right Trigger",
        }
        return axis_names.get(axis, f"Axis {axis}")
    
    def get_hat_direction_name(self, hat_value: Tuple[int, int]) -> str:
        """Get a descriptive name for a hat/d-pad direction."""
        directions = {
            (0, 0): "Center",
            (0, 1): "Up",
            (0, -1): "Down",
            (-1, 0): "Left",
            (1, 0): "Right",
            (-1, 1): "Up-Left",
            (1, 1): "Up-Right",
            (-1, -1): "Down-Left",
            (1, -1): "Down-Right",
        }
        return directions.get(hat_value, f"Hat {hat_value}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop all vibration
        self.stop_all_vibration()
        
        self._keyboard.clear()
        self.gamepads.clear()
        
        # Clear all callbacks
        self._on_key_press.clear()
        self._on_key_release.clear()
        self._on_mouse_press.clear()
        self._on_mouse_release.clear()
        self._on_mouse_move.clear()
        self._on_mouse_wheel.clear()
        self._on_gamepad_button_press.clear()
        self._on_gamepad_button_release.clear()
        self._on_gamepad_axis.clear()
        self._on_gamepad_hat.clear()
        self._on_gamepad_connect.clear()
        self._on_gamepad_disconnect.clear()
