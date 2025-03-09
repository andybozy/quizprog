# tests/test_navigator.py

import pytest
from quizlib.navigator import pick_a_file_menu, get_file_question_count

def test_get_file_question_count():
    questions = [
        {"_quiz_source": "/path/to/file1.json"},
        {"_quiz_source": "/path/to/file2.json"},
        {"_quiz_source": "/path/to/file1.json"},
        {"_quiz_source": "/some/other.json"}
    ]
    count1 = get_file_question_count(questions, "/path/to/file1.json")
    count2 = get_file_question_count(questions, "/path/to/file2.json")
    count3 = get_file_question_count(questions, "/not/there.json")

    assert count1 == 2
    assert count2 == 1
    assert count3 == 0


@pytest.mark.parametrize("user_inputs,expected_path", [
    # Single course, single section, single file
    (
        ["1", "1", "1"],  # user picks 1 for course, 1 for section, 1 for file
        "/some/path/to/fileA.json"
    ),
    # cancel at the course level
    (
        ["0"],  # user picks cancel
        None
    )
])
def test_pick_a_file_menu(monkeypatch, user_inputs, expected_path):
    # We only have 1 course, 1 section, 1 file
    # or we want to see if user cancels

    # We'll define a fake cursos_dict:
    fake_cursos_dict = {
        "CURSO1": {
            "sections": {
                "SEC-A": {
                    "files": [
                        {
                            "filename": "fileA.json",
                            "filepath": "/some/path/to/fileA.json",
                            "question_count": 10
                        }
                    ],
                    "section_questions": 10
                }
            },
            "total_files": 1,
            "total_questions": 10
        }
    }

    # Mock user input
    inputs_iter = iter(user_inputs)
    def fake_input(prompt=""):
        return next(inputs_iter)

    monkeypatch.setattr("builtins.input", fake_input)

    chosen_path = pick_a_file_menu(fake_cursos_dict)
    assert chosen_path == expected_path
