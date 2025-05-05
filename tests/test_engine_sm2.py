import pytest
import json
import quizlib.engine as eng
from quizlib.engine import preguntar
from datetime import date

@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 5, 5)
    monkeypatch.setattr(eng, "date", FixedDate)
    yield

def make_question_data(source_path):
    return {
        "question": "Test SM2?",
        "answers": [
            {"text": "Correct", "correct": True},
            {"text": "Wrong1", "correct": False},
            {"text": "Wrong2", "correct": False},
            {"text": "Wrong3", "correct": False},
        ],
        "explanation": "",
        "_quiz_source": source_path
    }

def test_sm2_initial_interval_and_ease(monkeypatch):
    # No shuffle, no screen clears or pauses
    monkeypatch.setattr(eng, "clear_screen", lambda: None)
    monkeypatch.setattr(eng, "press_any_key", lambda: None)
    # Always answer correctly
    monkeypatch.setattr("builtins.input", lambda prompt="": "A")

    perf_data = {}
    session_counts = {"correct":0, "wrong":0, "unanswered":0}
    qdata = make_question_data("root/CourseX/file.json")

    preguntar(0, qdata, perf_data, session_counts, disable_shuffle=True, exam_dates={})
    pd = perf_data["0"]

    assert pd["repetition"] == 1
    assert pd["interval"] == 1
    # ease starts at 2.5, then +0.1 = 2.6
    assert pytest.approx(pd["ease"], rel=1e-3) == 2.6

def test_sm2_interval_growth_and_exam_cap(monkeypatch):
    monkeypatch.setattr(eng, "clear_screen", lambda: None)
    monkeypatch.setattr(eng, "press_any_key", lambda: None)
    monkeypatch.setattr("builtins.input", lambda prompt="": "A")

    perf_data = {}
    session_counts = {"correct":0, "wrong":0, "unanswered":0}
    qdata = make_question_data("root/CourseY/file.json")

    # First correct → rep=1, interval=1, ease=2.6
    preguntar(0, qdata, perf_data, session_counts, disable_shuffle=True, exam_dates={})
    pd = perf_data["0"]
    assert pd["repetition"] == 1
    assert pd["interval"] == 1
    assert pytest.approx(pd["ease"], rel=1e-3) == 2.6

    # Second correct → rep=2, interval=3, ease=2.7
    preguntar(0, qdata, perf_data, session_counts, disable_shuffle=True, exam_dates={})
    pd = perf_data["0"]
    assert pd["repetition"] == 2
    assert pd["interval"] == 3
    old_ease = pd["ease"]

    # Third correct → rep=3, interval = round(3 * old_ease)
    preguntar(0, qdata, perf_data, session_counts, disable_shuffle=True, exam_dates={})
    pd = perf_data["0"]
    assert pd["repetition"] == 3
    assert pd["interval"] == round(3 * old_ease)

    # Fourth correct with exam cap at 2 days ahead
    exam_dates = {"CourseY": "2025-05-07"}  # two days later
    preguntar(0, qdata, perf_data, session_counts, disable_shuffle=True, exam_dates=exam_dates)
    pd = perf_data["0"]
    # Even though uncapped interval would be larger, it must be capped to days_left=2
    assert pd["interval"] == 2
