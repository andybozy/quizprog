# tests/test_engine.py

import pytest
import random
import re
import quizlib.engine as eng
from quizlib.engine import preguntar, clean_embedded_answers, remap_answer_references

@pytest.fixture
def monkeypatch_engine(monkeypatch):
    # Avoid screen clears and pauses in tests
    monkeypatch.setattr(eng, "clear_screen", lambda: None)
    monkeypatch.setattr(eng, "press_any_key", lambda: None)
    return monkeypatch

def test_clean_embedded_answers():
    text = """1) Title

a) Option A
b) Option B
blah
c) Option C
Hello
"""
    result = clean_embedded_answers(text)
    assert "Option A" not in result
    assert "Option B" not in result
    assert "Option C" not in result
    assert "blah" in result
    assert "Hello" in result

def test_remap_answer_references():
    mapping = {0: 1, 1: 0, 2: 2, 3: 3}
    text = "a y b y c"
    remapped = remap_answer_references(text, mapping)
    assert remapped == "A y B y C"

def test_preguntar_multiple_correct(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Pregunta con a) y b) correctas",
        "answers": [
            {"text": "Opción A", "correct": True},
            {"text": "Opción B", "correct": True},
            {"text": "Opción C", "correct": False},
            {"text": "Opción D", "correct": False},
        ],
        "explanation": "Porque a y b son correctas."
    }
    inputs = iter(["A,B"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    perf_data = {}
    session_counts = {"correct":0, "wrong":0, "unanswered":0}
    result = preguntar(0, question_data, perf_data, session_counts, disable_shuffle=True)
    assert result is True
    assert session_counts["correct"] == 1
    assert session_counts["wrong"] == 0

def test_preguntar_multi_delimiters(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Multi correct test: a) or c) ???",
        "answers": [
            {"text": "X", "correct": True},
            {"text": "Y", "correct": False},
            {"text": "Z", "correct": True},
            {"text": "W", "correct": False},
        ],
        "explanation": ""
    }
    perf_data = {}
    session_counts = {"correct":0, "wrong":0, "unanswered":0}
    for inp in ["A C","A,C","a c","a,c","A;C","A  C"]:
        inputs = iter([inp])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = preguntar(0, question_data, perf_data, session_counts, disable_shuffle=True)
        assert result is True, f"'{inp}' not accepted"

def test_preguntar_exit_confirm(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Q?",
        "answers":[{"text":"A","correct":True},{"text":"B","correct":False},
                   {"text":"C","correct":False},{"text":"D","correct":False}],
        "explanation": ""
    }
    inputs = iter(["0","s"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    perf_data = {}
    session_counts = {"correct":0,"wrong":0,"unanswered":0}
    result = preguntar(0, question_data, perf_data, session_counts, disable_shuffle=True)
    assert result is None
    assert session_counts["unanswered"] == 1
    assert perf_data["0"]["history"][-1] == "skipped"

def test_preguntar_exit_cancel(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Q?",
        "answers":[{"text":"A","correct":True},{"text":"B","correct":False},
                   {"text":"C","correct":False},{"text":"D","correct":False}],
        "explanation": ""
    }
    inputs = iter(["0","n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    perf_data = {}
    session_counts = {"correct":0,"wrong":0,"unanswered":0}
    result = preguntar(0, question_data, perf_data, session_counts, disable_shuffle=True)
    assert result is False
    assert session_counts["wrong"] == 1
    assert perf_data["0"]["history"][-1] == "wrong"

def test_shuffle_preserves_correctness():
    original = [
        {"text":"A","correct":True},
        {"text":"B","correct":False},
        {"text":"C","correct":True},
        {"text":"D","correct":False},
    ]
    before = {ans["text"] for ans in original if ans["correct"]}
    shuffled = original[:]
    random.shuffle(shuffled)
    after = {ans["text"] for ans in shuffled if ans["correct"]}
    assert after == before

def test_question_not_remapped_but_explanation_is_remapped(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "In this question mention a) or c) explicitly.",
        "answers":[{"text":"ref to a","correct":True},{"text":"ref to b","correct":False},
                   {"text":"ref to c","correct":False},{"text":"ref to d","correct":False}],
        "explanation":"Because a and b."
    }
    inputs = iter(["A"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    perf_data = {}
    session_counts = {"correct":0,"wrong":0,"unanswered":0}
    printed = []
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: printed.append(" ".join(str(a) for a in args)))
    result = preguntar(0, question_data, perf_data, session_counts, disable_shuffle=True)
    assert result is True
    out = "\n".join(printed)
    assert "mention a) or c) explicitly" in out
    assert "Because A and B." in out
    assert "ref to A" in out
    assert "ref to B" in out

def test_preguntar_empty_input_skips(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Skip test question?",
        "answers": [
            {"text": "A", "correct": True},
            {"text": "B", "correct": False},
            {"text": "C", "correct": False},
            {"text": "D", "correct": False},
        ],
        "explanation": ""
    }
    inputs = iter([""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    perf_data = {}
    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}
    result = preguntar(0, question_data, perf_data, session_counts, disable_shuffle=True)
    # pressing Enter should skip: quality=0 → return False
    assert result is False
    assert session_counts["unanswered"] == 1
    assert perf_data["0"]["history"][-1] == "skipped"