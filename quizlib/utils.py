# quizlib/utils.py

import os

def clear_screen():
    """Semplice clear dello schermo."""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def press_any_key():
    input("\nPresiona Enter para continuar...")
