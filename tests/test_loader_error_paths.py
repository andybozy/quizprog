import pytest
import os
from quizlib.loader import load_json_file

def test_load_json_file_missing_questions(tmp_path, caplog):
    f = tmp_path / "noq.json"
    f.write_text('{"foo": []}', encoding="utf-8")
    caplog.set_level("WARNING")
    data = load_json_file(str(f))
    assert data is None
    assert "Missing 'questions'" in caplog.text

def test_load_json_file_invalid_json(tmp_path, caplog):
    f = tmp_path / "bad.json"
    f.write_text('{bad json}', encoding="utf-8")
    caplog.set_level("WARNING")
    data = load_json_file(str(f))
    assert data is None
    assert "Error loading JSON" in caplog.text
