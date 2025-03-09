# quizlib/utils.py

import os
import sys

def clear_screen():
    """Legacy approach: repeatedly try to clear the terminal until successful."""
    done = False
    while not done:
        try:
            if os.name == 'nt':
                os.system('cls')
            else:
                os.system('clear')
            done = True
        except Exception:
            pass

def press_any_key():
    """Wait for user to press Enter."""
    input("\nPresiona Enter para continuar...")

# You can add other utility functions below if needed.
