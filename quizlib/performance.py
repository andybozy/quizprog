# quizprog/quizlib/performance.py

import os
import json

PERFORMANCE_FILE = "quiz_performance.json"

def load_performance_data(filepath=PERFORMANCE_FILE):
    """Load performance data or return {} if not found."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_performance_data(perf_data, filepath=PERFORMANCE_FILE):
    """Save the perf_data dict to the JSON file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")
