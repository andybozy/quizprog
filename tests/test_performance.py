# tests/test_performance.py

import pytest
import os
from quizlib.performance import load_performance_data, save_performance_data

def test_load_empty(tmp_path):
    f = tmp_path / "perf.json"
    data = load_performance_data(str(f))
    assert data == {}

def test_save_then_load(tmp_path):
    f = tmp_path / "perf.json"
    sample = {"0": {"wrong": False, "unanswered": True}}
    save_performance_data(sample, str(f))

    loaded = load_performance_data(str(f))
    assert loaded == sample
