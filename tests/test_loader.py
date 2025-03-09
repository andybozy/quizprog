# quizprog/tests/test_loader.py

import os
import pytest
from quizlib.loader import descubrir_quiz_files, load_json_file, load_all_quizzes

def test_discover_quiz_files(tmp_path):
    # make dummy structure
    data_dir = tmp_path / "dummy_quiz"
    data_dir.mkdir()
    (data_dir / "file1.json").write_text('{"questions":[]}', encoding="utf-8")
    (data_dir / "file2.txt").write_text("Not a JSON quiz", encoding="utf-8")

    result = descubrir_quiz_files(str(data_dir))
    assert len(result) == 1
    assert result[0].endswith("file1.json")

def test_load_json_file(tmp_path):
    f = tmp_path / "sample.json"
    f.write_text('{"questions":[{"question": "Test", "answers": []}]}', encoding="utf-8")
    data = load_json_file(str(f))
    assert "questions" in data
    assert len(data["questions"]) == 1

def test_load_all_quizzes(tmp_path):
    data_dir = tmp_path / "folder"
    data_dir.mkdir()
    # Note: use "question" key, not "q"
    (data_dir / "quiz.json").write_text('{"questions":[{"question": "Q1", "answers": []}]}', encoding="utf-8")

    combined, cursos_dict, cursos_archivos = load_all_quizzes(str(data_dir))
    assert len(combined) == 1
    assert len(cursos_dict) == 1
    assert len(cursos_archivos) == 1
