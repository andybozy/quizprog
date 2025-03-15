# quizlib/performance.py

import os
import json
import shutil

PERFORMANCE_FILE = "quiz_performance.json"

def load_performance_data(filepath=PERFORMANCE_FILE):
    """
    Carica i dati di performance da JSON. Se non esiste, ritorna un dict vuoto.
    """
    if not os.path.exists(filepath):
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except:
        return {}

def save_performance_data(perf_data, filepath=PERFORMANCE_FILE):
    """
    Salva perf_data in JSON. Fa un backup del file esistente.
    """
    if os.path.exists(filepath):
        backup_path = filepath + ".bak"
        try:
            shutil.copy2(filepath, backup_path)
        except:
            pass

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(perf_data, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"[!] Error guardando desempeño: {ex}")
