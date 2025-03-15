# tests/test_engine.py

import pytest
import random
import re
from quizlib.engine import preguntar, clean_embedded_answers, remap_answer_references
from quizlib.utils import clear_screen, press_any_key

@pytest.fixture
def monkeypatch_engine(monkeypatch):
    # Evitiamo di pulire lo schermo e chiedere input in test.
    monkeypatch.setattr("quizlib.engine.clear_screen", lambda: None)
    monkeypatch.setattr("quizlib.engine.press_any_key", lambda: None)
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
    # a->B, b->A, c->C => "B y A y C" => sort => "A y B y C"
    assert remapped == "A y B y C"

def test_preguntar_multiple_correct(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Pregunta con a) y b) correctas",
        "answers": [
            {"text": "Opción A", "correct": True},  # index=0 => A
            {"text": "Opción B", "correct": True},  # index=1 => B
            {"text": "Opción C", "correct": False}, # index=2 => C
            {"text": "Opción D", "correct": False}, # index=3 => D
        ],
        "explanation": "Porque a y b son correctas."
    }

    user_input = "A,B"
    inputs = iter([user_input])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    perf_data = {}
    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}
    result = preguntar(
        qid=0,
        question_data=question_data,
        perf_data=perf_data,
        session_counts=session_counts,
        disable_shuffle=True
    )
    assert result is True
    assert session_counts["correct"] == 1
    assert session_counts["wrong"] == 0

def test_preguntar_multi_delimiters(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "Multi correct test: a) or c) ???",
        "answers": [
            {"text": "X", "correct": True},   # idx=0 => A
            {"text": "Y", "correct": False},  # idx=1 => B
            {"text": "Z", "correct": True},   # idx=2 => C
            {"text": "W", "correct": False},  # idx=3 => D
        ],
        "explanation": ""
    }
    perf_data = {}
    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}

    test_inputs = ["A C", "A,C", "a c", "a,c", "A;C", "A  C"]
    for inp in test_inputs:
        answers_iter = iter([inp])
        monkeypatch.setattr("builtins.input", lambda _: next(answers_iter))

        if "0" in perf_data:
            del perf_data["0"]

        result = preguntar(
            qid=0,
            question_data=question_data,
            perf_data=perf_data,
            session_counts=session_counts,
            disable_shuffle=True
        )
        assert result is True, f"Input '{inp}' was not accepted as correct"

def test_shuffle_preserves_correctness():
    original_answers = [
        {"text": "Answer A", "correct": True},
        {"text": "Answer B", "correct": False},
        {"text": "Answer C", "correct": True},
        {"text": "Answer D", "correct": False},
    ]
    correct_before = {ans["text"] for ans in original_answers if ans["correct"]}

    shuffled = original_answers[:]
    random.shuffle(shuffled)
    correct_after = {ans["text"] for ans in shuffled if ans["correct"]}

    assert correct_after == correct_before

def test_question_not_remapped_but_explanation_is_remapped(monkeypatch_engine, monkeypatch):
    question_data = {
        "question": "In this question, we mention a) or c) explicitly (DO NOT CHANGE).",
        "answers": [
            {"text": "References to a in answer text", "correct": True},
            {"text": "References to b in answer text", "correct": False},
        ],
        "explanation": "Explanation referencing a and b - these should get mapped."
    }

    inputs = iter(["A"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    perf_data = {}
    session_counts = {"correct": 0, "wrong": 0, "unanswered": 0}

    printed_lines = []
    def fake_print(*args, **kwargs):
        line = " ".join(str(a) for a in args)
        printed_lines.append(line)

    monkeypatch.setattr("builtins.print", fake_print)

    result = preguntar(
        qid=0,
        question_data=question_data,
        perf_data=perf_data,
        session_counts=session_counts,
        disable_shuffle=True
    )
    assert result is True
    assert session_counts["correct"] == 1

    joined_output = "\n".join(printed_lines)
    # The question text must remain unchanged
    assert "mention a) or c) explicitly (DO NOT CHANGE)" in joined_output
    # The explanation references 'a' and 'b' => expected to be mapped to 'A' and 'B'
    assert "Explanation referencing A and B" in joined_output
    # The answer text references 'a' => 'A', 'b' => 'B'
    assert "References to A in answer text" in joined_output
    assert "References to B in answer text" in joined_output
