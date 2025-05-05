import pytest
import quizlib.engine as eng
from quizlib.engine import remap_answer_references, colorize_answers

def test_remap_answer_references_sorting_and_mapping():
    mapping = {0:2, 2:0, 1:1, 3:3}
    text = "a y b y c y d"
    # a→C, b→B, c→A, d→D yields "C y B y A y D" then sorted -> "A y B y C y D"
    remapped = remap_answer_references(text, mapping)
    assert remapped == "A y B y C y D"

def test_colorize_answers():
    question_text = "Q?"
    shuffled_answers = [
        {"text":"OptA","correct":True},
        {"text":"OptB","correct":False},
        {"text":"OptC","correct":False},
        {"text":"OptD","correct":False},
    ]
    # identity mapping
    shuffle_mapping = {0:0,1:1,2:2,3:3}
    user_letters_set = {"B"}
    correct_letters_set = {"A"}

    output = colorize_answers(
        question_text,
        shuffled_answers,
        shuffle_mapping,
        user_letters_set,
        correct_letters_set
    )

    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"

    # Correct answer 'A' should be wrapped in GREEN
    assert f"[{GREEN}A{RESET}]" in output
    # User‐selected wrong 'B' should be wrapped in RED
    assert f"[{RED}B{RESET}]" in output
    # Other options show default/reset color
    assert f"[{RESET}C{RESET}]" in output
    assert f"[{RESET}D{RESET}]" in output
