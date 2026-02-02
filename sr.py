"""
sr.py - Screen Reader Speech Abstraction Module
================================================
A high-performance speech output abstraction layer optimized for
audiogame and accessible application development.

Optimized for frequent repeated calls to speak() in game loops.

Features:
    - Automatic initialization with lazy loading
    - Minimal overhead on hot path (speak calls)
    - Screen reader detection
    - Speech output with interrupt control
    - Braille output support
    - Thread-safe initialization
    - Graceful fallback handling

Usage:
    Basic usage (auto-initializes on first call):
        from sr import speak, silence
        speak("Hello world!")
        speak("This interrupts", interrupt=True)
        speak("This queues", interrupt=False)
        silence()

    Check screen reader status:
        from sr import get_active_screen_reader, is_screen_reader_active
        if is_screen_reader_active():
            print(f"Using: {get_active_screen_reader()}")

    Explicit initialization (optional, for startup control):
        from sr import initialize, shutdown
        initialize()  # Load now instead of on first speak()
        # ... application ...
        shutdown()  # Optional, auto-cleanup on exit

Requirements:
    - cytolk (pip install cytolk)
    - A supported screen reader (NVDA, JAWS, etc.) or SAPI fallback

Author: Audiogame Development Project
License: MIT
"""

from __future__ import annotations

import atexit
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cytolk import tolk as TolkModule


class ScreenReaderError(Exception):
    """Exception raised for screen reader related errors."""
    pass


# -----------------------------------------------------------------------------
# Module-level state (optimized for fast access)
# -----------------------------------------------------------------------------

# Direct reference to tolk module after initialization (avoids repeated imports)
_tolk: Optional[TolkModule] = None

# Fast boolean check - avoids method calls on hot path
_ready: bool = False

# Lock only used during initialization, not on every speak() call
_init_lock: threading.Lock = threading.Lock()

# Track if we've registered the atexit handler
_atexit_registered: bool = False


# -----------------------------------------------------------------------------
# Initialization and Cleanup
# -----------------------------------------------------------------------------

def _register_cleanup() -> None:
    """Register cleanup handler (called once during init)."""
    global _atexit_registered
    if not _atexit_registered:
        atexit.register(_cleanup)
        _atexit_registered = True


def _cleanup() -> None:
    """Cleanup handler for program exit."""
    global _tolk, _ready
    if _ready and _tolk is not None:
        try:
            _tolk.unload()
        except Exception:
            pass
        _tolk = None
        _ready = False


def initialize() -> bool:
    """
    Initialize the screen reader system.
    
    This is called automatically on first use of speak(), silence(), etc.
    Call explicitly only if you need to control initialization timing
    (e.g., to handle errors at startup rather than during gameplay).
    
    Returns:
        bool: True if initialization succeeded.
    
    Raises:
        ScreenReaderError: If cytolk is not installed.
    """
    global _tolk, _ready
    
    # Fast path: already initialized
    if _ready:
        return True
    
    # Slow path: need to initialize (thread-safe)
    with _init_lock:
        # Double-check after acquiring lock
        if _ready:
            return True
        
        try:
            from cytolk import tolk
            tolk.load()
            _tolk = tolk
            _ready = True
            _register_cleanup()
            return True
            
        except ImportError:
            raise ScreenReaderError(
                "cytolk library not found. Install with: pip install cytolk"
            )
        except Exception as e:
            raise ScreenReaderError(f"Failed to initialize screen reader: {e}")


def shutdown() -> None:
    """
    Shutdown the screen reader system and release resources.
    
    This is optional - cleanup happens automatically on program exit.
    Call this only if you need to release resources before exit.
    """
    global _tolk, _ready
    
    if not _ready:
        return
    
    with _init_lock:
        if not _ready:
            return
        
        try:
            if _tolk is not None:
                _tolk.unload()
        except Exception:
            pass
        finally:
            _tolk = None
            _ready = False


def _ensure_ready() -> bool:
    """
    Ensure the system is initialized. Returns False if unavailable.
    
    This is the internal fast-path check used by all functions.
    """
    if _ready:
        return True
    
    try:
        initialize()
        return _ready
    except ScreenReaderError:
        return False


# -----------------------------------------------------------------------------
# Core Speech Functions (Optimized Hot Path)
# -----------------------------------------------------------------------------

def speak(text: str = "", interrupt: bool = True) -> bool:
    """
    Speak text through the screen reader.
    
    Optimized for frequent calls in game loops. After initialization,
    this function has minimal overhead.
    
    Args:
        text: The text to speak. Empty strings are silently ignored.
        interrupt: If True (default), stop any current speech before
                  speaking. If False, queue the text after current speech.
    
    Returns:
        bool: True if the text was successfully sent to the screen reader.
    
    Example:
        speak("Hello world!")
        speak("This interrupts previous speech")
        speak("This is queued", interrupt=False)
    """
    # Fast path: empty text
    if not text:
        return True
    
    # Fast path: already initialized
    if _ready:
        try:
            _tolk.speak(text, interrupt)
            return True
        except Exception:
            return False
    
    # Slow path: need initialization
    if not _ensure_ready():
        return False
    
    try:
        _tolk.speak(text, interrupt)
        return True
    except Exception:
        return False


def silence() -> bool:
    """
    Stop any current speech immediately.
    
    Returns:
        bool: True if silence command was successful.
    """
    if _ready:
        try:
            _tolk.silence()
            return True
        except Exception:
            return False
    
    if not _ensure_ready():
        return False
    
    try:
        _tolk.silence()
        return True
    except Exception:
        return False


def braille(text: str) -> bool:
    """
    Output text to a braille display.
    
    Args:
        text: The text to display on the braille device.
    
    Returns:
        bool: True if the text was successfully sent to the braille display.
    """
    if not text:
        return True
    
    if _ready:
        try:
            _tolk.braille(text)
            return True
        except Exception:
            return False
    
    if not _ensure_ready():
        return False
    
    try:
        _tolk.braille(text)
        return True
    except Exception:
        return False


def output(text: str, interrupt: bool = True) -> bool:
    """
    Output text to both speech and braille simultaneously.
    
    Args:
        text: The text to output.
        interrupt: If True, interrupt current speech.
    
    Returns:
        bool: True if output was successful.
    """
    if not text:
        return True
    
    if _ready:
        try:
            _tolk.output(text, interrupt)
            return True
        except Exception:
            return False
    
    if not _ensure_ready():
        return False
    
    try:
        _tolk.output(text, interrupt)
        return True
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Status Query Functions
# -----------------------------------------------------------------------------

def get_active_screen_reader() -> Optional[str]:
    """
    Get the name of the currently active screen reader.
    
    Returns:
        str | None: Name of the active screen reader (e.g., "NVDA", "JAWS"),
                   or None if no screen reader is detected.
    """
    if not _ensure_ready():
        return None
    
    try:
        name = _tolk.detect_screen_reader()
        return name if name else None
    except Exception:
        return None


def is_screen_reader_active() -> bool:
    """
    Check if a screen reader is currently active.
    
    Returns:
        bool: True if a screen reader is detected and active.
    """
    if not _ensure_ready():
        return False
    
    try:
        return _tolk.has_screen_reader()
    except Exception:
        return False


def has_speech() -> bool:
    """
    Check if speech output is available.
    
    Returns:
        bool: True if speech is available (via screen reader or SAPI).
    """
    if not _ensure_ready():
        return False
    
    try:
        return _tolk.has_speech()
    except Exception:
        return False


def has_braille() -> bool:
    """
    Check if braille output is available.
    
    Returns:
        bool: True if a braille display is available.
    """
    if not _ensure_ready():
        return False
    
    try:
        return _tolk.has_braille()
    except Exception:
        return False


def is_speaking() -> bool:
    """
    Check if the screen reader is currently speaking.
    
    Note: This may not be supported by all screen readers.
    
    Returns:
        bool: True if currently speaking, False otherwise.
    """
    if not _ensure_ready():
        return False
    
    try:
        return _tolk.is_speaking()
    except Exception:
        return False


def is_loaded() -> bool:
    """
    Check if the speech system is initialized and ready.
    
    This is a fast check with no side effects - it won't trigger
    initialization if not already done.
    
    Returns:
        bool: True if the system is ready for use.
    """
    return _ready


# -----------------------------------------------------------------------------
# Optional: ScreenReader class for those who prefer OOP style
# -----------------------------------------------------------------------------

class ScreenReader:
    """
    Object-oriented wrapper around the module functions.
    
    This is a lightweight facade - all instances share the same
    underlying module state. Provided for those who prefer OOP style
    or need context manager support.
    
    Example:
        with ScreenReader() as sr:
            sr.speak("Hello!")
        
        # Or without context manager:
        sr = ScreenReader()
        sr.speak("Hello!")  # Auto-initializes
    """
    
    __slots__ = ()  # No instance attributes needed
    
    def __enter__(self) -> ScreenReader:
        initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Don't shutdown here - other code might still need it
        # Cleanup happens automatically at program exit
        return False
    
    @staticmethod
    def speak(text: str = "", interrupt: bool = True) -> bool:
        return speak(text, interrupt)
    
    @staticmethod
    def silence() -> bool:
        return silence()
    
    @staticmethod
    def braille(text: str) -> bool:
        return braille(text)
    
    @staticmethod
    def output(text: str, interrupt: bool = True) -> bool:
        return output(text, interrupt)
    
    @staticmethod
    def initialize() -> bool:
        return initialize()
    
    @staticmethod
    def shutdown() -> None:
        shutdown()
    
    @property
    def is_initialized(self) -> bool:
        return _ready
    
    @property
    def active_reader(self) -> Optional[str]:
        return get_active_screen_reader()
    
    @staticmethod
    def is_active() -> bool:
        return is_screen_reader_active()
    
    @staticmethod
    def has_speech() -> bool:
        return has_speech()
    
    @staticmethod
    def has_braille() -> bool:
        return has_braille()
    
    @staticmethod
    def is_speaking() -> bool:
        return is_speaking()