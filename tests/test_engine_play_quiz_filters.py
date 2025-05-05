import pytest
import quizlib.engine as eng
from quizlib.engine import play_quiz

@pytest.fixture(autouse=True)
def dummy_preguntar(monkeypatch):
    called = []
    def fake(qid, question_data, perf_data, session_counts,
             disable_shuffle, exam_dates, position, total):
        called.append((qid, position, total))
        return True
    monkeypatch.setattr(eng, "preguntar", fake)
    return called

def make_questions(n):
    return [
        {
            "question": f"Q{i}",
            "answers":[
                {"text":"A","correct":True},
                {"text":"B","correct":False},
                {"text":"C","correct":False},
                {"text":"D","correct":False}
            ],
            "_quiz_source":"f"
        }
        for i in range(n)
    ]

def test_play_quiz_all(dummy_preguntar):
    questions = make_questions(3)
    perf_data = {}
    play_quiz(questions, perf_data, filter_mode="all", file_filter=None, exam_dates={})
    assert dummy_preguntar == [(0,1,3),(1,2,3),(2,3,3)]

def test_play_quiz_unanswered(dummy_preguntar):
    questions = make_questions(3)
    perf_data = {"1": {"history":["correct"], "next_review":"2025-05-05"}}
    play_quiz(questions, perf_data, filter_mode="unanswered", file_filter=None, exam_dates={})
    # only Q0 and Q2 are unanswered
    assert dummy_preguntar == [(0,1,2),(2,2,2)]

def test_play_quiz_wrong(dummy_preguntar):
    questions = make_questions(3)
    perf_data = {
        "0": {"history":["wrong"], "next_review":"2025-05-05"},
        "1": {"history":["correct"], "next_review":"2025-05-05"}
    }
    play_quiz(questions, perf_data, filter_mode="wrong", file_filter=None, exam_dates={})
    # only Q0
    assert dummy_preguntar == [(0,1,1)]

def test_play_quiz_wrong_unanswered(dummy_preguntar):
    questions = make_questions(4)
    perf_data = {
        "0": {"history":["wrong"], "next_review":"2025-05-05"},
        "1": {"history":["skipped"], "next_review":"2025-05-05"},
        "2": {"history":["correct"], "next_review":"2025-05-05"}
    }
    play_quiz(questions, perf_data, filter_mode="wrong_unanswered", file_filter=None, exam_dates={})
    # subset: Q0 (wrong), Q1 (skipped) → ordered by wrong count descending
    assert dummy_preguntar == [(0,1,2),(1,2,2)]
