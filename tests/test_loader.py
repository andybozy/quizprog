# tests/test_loader.py

import pytest
from quizlib.loader import discover_quiz_files, load_json_file, load_all_quizzes
import os
import json

def test_discover_quiz_files(tmp_path):
    data_dir = tmp_path / "quizzes"
    data_dir.mkdir()
    (data_dir / "quiz1.json").write_text('{"questions":[{"question":"Q1","answers":[]}]}', encoding="utf-8")
    (data_dir / "notes.txt").write_text("Not a JSON quiz", encoding="utf-8")

    found = discover_quiz_files(str(data_dir))
    assert len(found) == 1
    assert found[0].endswith("quiz1.json")

def test_load_json_file(tmp_path):
    f = tmp_path / "quiz.json"
    f.write_text('{"questions":[{"question":"Sample?","answers":[]}]}', encoding="utf-8")
    data = load_json_file(str(f))
    assert "questions" in data
    assert len(data["questions"]) == 1

def test_load_all_quizzes(tmp_path):
    d = tmp_path / "some_quizzes"
    d.mkdir()
    qf = d / "test.json"
    qf.write_text('{"questions":[{"question":"OK?","answers":[]}]}', encoding="utf-8")

    combined, cursos, info = load_all_quizzes(str(d))
    assert len(combined) == 1
    assert len(cursos) == 1
    assert len(info) == 1
