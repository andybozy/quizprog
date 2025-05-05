# tests/test_engine_due.py

import pytest
import quizlib.engine as eng
from quizlib.engine import play_quiz
from datetime import date, datetime

@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 5, 5)
    monkeypatch.setattr(eng, "date", FixedDate)
    yield

def test_play_quiz_due_filter(monkeypatch):
    questions = [
        {"question":"Q0","answers":[{"text":"A","correct":True},{"text":"B","correct":False},
                                   {"text":"C","correct":False},{"text":"D","correct":False}], "_quiz_source":"f"},
        {"question":"Q1","answers":[{"text":"A","correct":True},{"text":"B","correct":False},
                                   {"text":"C","correct":False},{"text":"D","correct":False}], "_quiz_source":"f"},
        {"question":"Q2","answers":[{"text":"A","correct":True},{"text":"B","correct":False},
                                   {"text":"C","correct":False},{"text":"D","correct":False}], "_quiz_source":"f"},
    ]
    perf_data = {
        "0": {"next_review": "2025-05-05"},
        "1": {"next_review": "2025-05-06"},
    }
    called = []
    def fake_preguntar(qid, question_data, perf_data, session_counts,
                       disable_shuffle, exam_dates, position, total):
        called.append((qid, position, total))
        return True
    monkeypatch.setattr(eng, "preguntar", fake_preguntar)
    play_quiz(questions, perf_data, filter_mode="due", file_filter=None, exam_dates={})
    assert called == [(0,1,2),(2,2,2)]
