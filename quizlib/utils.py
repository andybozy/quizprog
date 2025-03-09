# quizlib/utils.py

import os

def clear_screen():
    """Cross-platform screen clear."""
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except:
        pass

def press_any_key():
    """Wait for user to press Enter."""
    input("\nPresiona Enter para continuar...")
