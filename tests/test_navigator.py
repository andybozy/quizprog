# tests/test_navigator.py

import pytest
from quizlib.navigator import pick_a_file_menu, get_file_question_count

def test_get_file_question_count():
    questions = [
        {"_quiz_source": "f1.json"},
        {"_quiz_source": "f2.json"},
        {"_quiz_source": "f1.json"}
    ]
    assert get_file_question_count(questions, "f1.json") == 2
    assert get_file_question_count(questions, "f2.json") == 1
    assert get_file_question_count(questions, "f3.json") == 0

def test_pick_a_file_menu(monkeypatch):
    cursos = {
        "Curso1": {
            "sections": {
                "(No subfolder)": {
                    "files": [
                        {"filename":"quizA.json","filepath":"/path/quizA.json","question_count":5}
                    ],
                    "section_questions":5
                }
            },
            "total_files":1,
            "total_questions":5
        }
    }
    inputs = iter(["1","1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    chosen = pick_a_file_menu(cursos)
    assert chosen == "/path/quizA.json"
