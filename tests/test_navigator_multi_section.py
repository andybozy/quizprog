import pytest
from quizlib.navigator import pick_a_file_menu

def test_pick_a_file_menu_multi_section(monkeypatch):
    cursos = {
        "Curso1": {
            "sections": {
                "SecA": {
                    "files":[{"filename":"fA.json","filepath":"/path/A.json","question_count":1}],
                    "section_questions":1
                },
                "SecB": {
                    "files":[{"filename":"fB.json","filepath":"/path/B.json","question_count":2}],
                    "section_questions":2
                }
            },
            "total_files":2,
            "total_questions":3
        }
    }
    # inputs: select course 1, then section 2, then file 1
    inputs = iter(["1","2","1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    chosen = pick_a_file_menu(cursos)
    assert chosen == "/path/B.json"
