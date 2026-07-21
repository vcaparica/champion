"""
main.py - Champion Entry Point
===============================
Main entry point for Champion audiogame.

Initializes pygame and joystick subsystems, creates the App instance,
and runs the main menu.

Usage:
    python main.py
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
