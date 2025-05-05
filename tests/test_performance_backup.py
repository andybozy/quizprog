import os
import json
import pytest
from quizlib.performance import load_performance_data, save_performance_data

def test_save_performance_creates_backup(tmp_path):
    perf_file = tmp_path / "perf.json"
    initial = {"x": 1}
    # Write initial data
    with open(perf_file, "w", encoding="utf-8") as f:
        json.dump(initial, f)
    # Save new data
    new_data = {"y": 2}
    save_performance_data(new_data, str(perf_file))

    backup = str(perf_file) + ".bak"
    assert os.path.exists(backup)

    # Backup still has initial contents
    with open(backup, "r", encoding="utf-8") as f:
        bak = json.load(f)
    assert bak == initial

    # Main file was overwritten
    loaded = load_performance_data(str(perf_file))
    assert loaded == new_data
