# quizprog/tests/test_performance.py
import pytest
from quizlib.performance import load_performance_data, save_performance_data
import os

def test_perf_load_empty(tmp_path):
    f = tmp_path / "perf.json"
    data = load_performance_data(str(f))
    assert data == {}

def test_perf_save_then_load(tmp_path):
    f = tmp_path / "perf.json"
    sample = {"10": {"wrong": True, "unanswered": False}}
    save_performance_data(sample, str(f))

    loaded = load_performance_data(str(f))
    assert loaded == sample
