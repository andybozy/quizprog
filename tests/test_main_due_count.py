# tests/test_main_due_count.py

import pytest
from datetime import date

def test_comando_resumen_archivos_programadas(monkeypatch, capsys):
    import quizlib.main as mainmod

    # 1) Monkey-patch out all screen-clearing, pauses, and fix “today”
    monkeypatch.setattr(mainmod, "clear_screen", lambda: None)
    monkeypatch.setattr(mainmod, "press_any_key", lambda: None)
    monkeypatch.setattr(mainmod, "effective_today", lambda: date(2025, 5, 10))
    monkeypatch.setattr(mainmod, "QUIZ_DATA_FOLDER", "quiz_data")

    # 2) Prepare a single file with 3 questions (IDs "1","2","3")
    fpath = "quiz_data/f.json"
    questions = [
        {"_quiz_id": "1", "_quiz_source": fpath},
        {"_quiz_id": "2", "_quiz_source": fpath},
        {"_quiz_id": "3", "_quiz_source": fpath},
    ]

    # 3) Perf data: 1 → next_review before today (due),
    #             2 → after today (not due),
    #             3 → no next_review (treated as due)
    perf_data = {
        "1": {"next_review": "2025-05-09", "history": ["correct"]},
        "2": {"next_review": "2025-05-11", "history": ["correct"]},
        "3": {"history": []},
    }

    # 4) One file in quiz_files_info—counts total=3
    quiz_files_info = [{"filepath": fpath, "filename": "f.json", "question_count": 3}]
    # course summary is irrelevant here; can be empty
    cursos_dict = {}

    # 5) Run and capture
    # The loop ends when the user types "0"
    monkeypatch.setattr("builtins.input", lambda prompt="": "0")
    mainmod.comando_resumen_archivos(questions, perf_data, cursos_dict, quiz_files_info)
    out = capsys.readouterr().out

    # 6) Verify that exactly 2 questions are shown as "programadas"
    assert "programadas=2 (66.7%)" in out
