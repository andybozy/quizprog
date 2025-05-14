# quizlib/utils.py

import os
import sys

def clear_screen():
    """
    Clear the screen if we have a real terminal.
    Skip if TERM is not set or stdout is not a TTY.
    """
    if not os.environ.get('TERM') or not sys.stdout.isatty():
        return
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


def press_any_key():
    """
    Pause only if we're attached to a real TTY.
    Otherwise skip silently.
    """
    if sys.stdin.isatty():
        input("\nPresiona Enter para continuar...")
