# quizlib/utils.py

import os

def clear_screen():
    """Legacy approach: keep trying to clear until it succeeds."""
    done = False
    while not done:
        try:
            if os.name == 'nt':
                os.system('cls')
            else:
                os.system('clear')
            done = True
        except:
            pass

def press_any_key():
    input("\nPresiona Enter para continuar...")
