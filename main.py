"""
main.py - Entry Point
=====================
Main entry point for the audiogame template.

Initializes pygame and joystick subsystems, creates the App instance,
and runs the main menu.

Usage:
    python main.py

Author: Audiogame Development Project
License: MIT
"""

from app import App
import pygame


def main():
    """Initialize pygame and run the application."""
    pygame.init()
    pygame.joystick.init()  # Enable gamepad support
    
    app = App()
    app.main_menu()
    
    pygame.quit()


if __name__ == "__main__":
    main()
