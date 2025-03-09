# quizprog/tests/test_engine.py

import pytest
from quizlib.engine import sanitize_question_text

def test_sanitize_question_text():
    text = """1) Something here

a) Option A
b) Option B
c) Option C
d) Option D
"""
    sanitized = sanitize_question_text(text)
    # We expect lines starting with 'a) b) c) d)' to be removed
    assert "Option A" not in sanitized
    assert "Option B" not in sanitized
    assert "Option C" not in sanitized
    assert "Option D" not in sanitized
    # We do expect "1) Something here"
    assert "Something here" in sanitized
