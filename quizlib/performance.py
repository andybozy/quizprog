import os
import json
import shutil

PERFORMANCE_FILE = "quiz_performance.json"

def load_performance_data(filepath=PERFORMANCE_FILE):
    """
    Load performance data from JSON.
    If the file doesn't exist or is invalid, return an empty dict.
    """
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                # Could be corrupted / unexpected structure
                return {}
            return data
    except:
        # If there's an error (e.g., JSON corruption), return empty
        return {}

def save_performance_data(perf_data, filepath=PERFORMANCE_FILE):
    """
    Save the perf_data dict to JSON.
    Before overwriting the existing file, make a backup to filepath + '.bak'.
    """
    # If file exists, back it up first
    if os.path.exists(filepath):
        backup_path = filepath + ".bak"
        try:
            shutil.copy2(filepath, backup_path)
        except Exception:
            # If backup fails for some reason, we ignore and proceed
            pass

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")
