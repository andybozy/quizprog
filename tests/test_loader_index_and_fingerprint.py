import pytest
import json
import os
from quizlib.loader import (
    fingerprint_question,
    load_index,
    save_index,
    load_all_quizzes,
)

def test_fingerprint_stability_and_difference():
    q1 = {"question": "Q?", "answers":[{"text":"A","correct":True},{"text":"B","correct":False}]}
    q2 = {"question": " Q? ", "answers":[{"text":"A","correct":True},{"text":"B","correct":False}]}
    # Same semantic content → same fingerprint
    assert fingerprint_question(q1) == fingerprint_question(q2)

    q3 = {"question": "Q!!", "answers":[{"text":"A","correct":True},{"text":"B","correct":False}]}
    # Different question text → different fingerprint
    assert fingerprint_question(q1) != fingerprint_question(q3)

def test_load_index_missing(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    idx = load_index(str(folder))
    assert idx == {"next_id":1, "files":{}, "fingerprint_to_id":{}, "archived":[]}

def test_load_index_corrupt(tmp_path, caplog):
    folder = tmp_path / "data"
    folder.mkdir()
    bad = folder / ".quiz_index.json"
    bad.write_text("not json", encoding="utf-8")
    caplog.set_level("WARNING")
    idx = load_index(str(folder))
    assert "Could not load quiz-index" in caplog.text
    assert idx["next_id"] == 1

def test_save_index(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    idx_in = {"next_id":5, "files":{}, "fingerprint_to_id":{}, "archived":[]}
    save_index(str(folder), idx_in)
    path = folder / ".quiz_index.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["next_id"] == 5

def test_archive_on_file_removal(tmp_path):
    # Create a quiz folder and a first quiz
    folder = tmp_path / "quiz_data"
    folder.mkdir()
    f1 = folder / "a.json"
    f1.write_text(json.dumps({
        "questions":[{"question":"One","answers":[{"text":"O","correct":True}]}]
    }), encoding="utf-8")

    # First load → builds index
    load_all_quizzes(str(folder))
    idx1 = json.loads((folder/".quiz_index.json").read_text(encoding="utf-8"))
    old_ids = list(idx1["fingerprint_to_id"].values())

    # Remove the first file, add a new one
    f1.unlink()
    f2 = folder / "b.json"
    f2.write_text(json.dumps({
        "questions":[{"question":"Two","answers":[{"text":"T","correct":True}]}]
    }), encoding="utf-8")

    # Second load → should archive old_ids
    load_all_quizzes(str(folder))
    idx2 = json.loads((folder/".quiz_index.json").read_text(encoding="utf-8"))
    for qid in old_ids:
        assert qid in idx2["archived"]
